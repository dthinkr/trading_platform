import asyncio
import io
from datetime import timedelta, datetime
from uuid import UUID, uuid4

from fastapi import (
    FastAPI, WebSocket, HTTPException, WebSocketDisconnect, 
    BackgroundTasks, Depends, status, Request
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_400_BAD_REQUEST
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
import polars as pl
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder
from core.trader_manager import TraderManager
from core.data_models import TraderType, TradingParameters, UserRegistration
from .auth import get_current_user, get_current_admin_user, get_firebase_auth
from .calculate_metrics import process_log_file, write_to_csv
from firebase_admin import auth
import secrets
import logging
import traceback
import json
from pydantic import BaseModel
import os
from fastapi import HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List

app = FastAPI()
security = HTTPBasic()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

trader_managers = {}
trader_to_session_lookup = {}
trader_manager: TraderManager = None

persistent_settings = {}

class PersistentSettings(BaseModel):
    settings: dict

@app.post("/admin/update_persistent_settings")
async def update_persistent_settings(settings: PersistentSettings):
    global persistent_settings
    persistent_settings = settings.settings
    return {"status": "success", "message": "Persistent settings updated"}

@app.get("/admin/get_persistent_settings")
async def get_persistent_settings():
    return {"status": "success", "data": persistent_settings}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")

@app.post("/user/login")
async def user_login(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    try:
        token = auth_header.split('Bearer ')[1]
        
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        uid = decoded_token['uid']
        
        session_id, trader_id = await find_or_create_session_and_assign_trader(uid)
        
        return {
            "status": "success",
            "message": "Login successful and trader assigned",
            "data": {
                "username": decoded_token.get('email'),
                "is_admin": False,
                "session_id": session_id,
                "trader_id": trader_id
            }
        }
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/admin/login")
async def admin_login(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "admin")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {
        "status": "success",
        "message": "Admin login successful",
        "data": {
            "username": "admin",
            "is_admin": True
        }
    }

@app.get("/traders/defaults")
async def get_trader_defaults():
    schema = TradingParameters.model_json_schema()
    defaults = {
        field: {
            "default": props.get("default"),
            "title": props.get("title"),
            "type": props.get("type"),
            "hint": props.get("description"),
        }
        for field, props in schema.get("properties", {}).items()
    }
    return JSONResponse(content={"status": "success", "data": defaults})

@app.post("/trading/initiate")
async def create_trading_session(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    global persistent_settings
    
    try:
        merged_params = TradingParameters.from_dict(persistent_settings)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    uid = current_user['uid']
    
    try:
        trader_id = f"HUMAN_{uid}"
        session_id = trader_to_session_lookup.get(trader_id)
        
        if not session_id:
            raise HTTPException(status_code=404, detail="No active session found for this user")
        
        trader_manager = trader_managers[session_id]
        
        trader_manager.params = merged_params
        
        if len(trader_manager.human_traders) == trader_manager.params.num_human_traders:
            background_tasks.add_task(trader_manager.launch)
        
        return {
            "status": "success",
            "message": "Trading session info retrieved",
            "data": {
                "trading_session_uuid": session_id,
                "trader_id": trader_id,
                "traders": list(trader_manager.traders.keys()),
                "human_traders": [t.id for t in trader_manager.human_traders],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving trading session info")
        
def get_manager_by_trader(trader_id: str):
    if trader_id not in trader_to_session_lookup.keys():
        return None
    trading_session_id = trader_to_session_lookup[trader_id]
    manager = trader_managers[trading_session_id]
    return manager

@app.get("/trader/{trader_id}")
async def get_trader(trader_id: str, current_user: dict = Depends(get_current_user)):
    trader_manager = get_manager_by_trader(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader = trader_manager.traders.get(trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader_data = trader.get_trader_params_as_dict()
    data = trader_manager.get_params()
    data["goal"] = trader_data["goal"]
    return {"status": "success", "message": "Trader found", "data": data}

@app.get("/trader_info/{trader_id}")
async def get_trader_info(trader_id: str, current_user: dict = Depends(get_current_user)):
    trader_manager = get_manager_by_trader(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = trader_manager.get_trader(trader_id)
    
    def is_jsonable(x):
        try:
            json.dumps(x)
            return True
        except (TypeError, OverflowError):
            return False

    all_attributes = {
        attr: getattr(trader, attr)
        for attr in dir(trader)
        if not attr.startswith('_') and not callable(getattr(trader, attr)) and attr != 'trading_session'
    }
    
    serializable_attributes = {k: v for k, v in all_attributes.items() if is_jsonable(v)}

    trader_info = {
        "status": "success",
        "message": "Trader found",
        "data": {
            "cash": trader.cash,
            "goal": trader.goal,
            "shares": trader.shares,
            "orders": trader.orders,
            "filled_orders": trader.filled_orders,
            "placed_orders": trader.placed_orders,
            "delta_cash": trader.delta_cash,
            "initial_cash": trader.initial_cash,
            "initial_shares": trader.initial_shares,
            "all_attributes": serializable_attributes
        },
    }
    
    return trader_info
    
@app.get("/trader/{trader_id}/session")
async def get_trader_session(trader_id: str, current_user: dict = Depends(get_current_user)):
    session_id = trader_to_session_lookup.get(trader_id)
    if not session_id:
        raise HTTPException(status_code=404, detail="No session found for this trader")
    
    trader_manager = trader_managers.get(session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader manager not found")

    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]

    response_data = {
        "status": "success",
        "data": {
            "trading_session_uuid": trader_manager.trading_session.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": human_traders_data,
            "game_params": trader_manager.params.model_dump()
        },
    }
    
    return response_data

@app.get("/traders/list")
async def list_traders(current_user: dict = Depends(get_current_admin_user)):
    return {
        "status": "success",
        "message": "List of traders",
        "data": {"traders": list(trader_manager.traders.keys())},
    }


@app.get("/")
async def root():
    return {
        "status": "trading is active",
        "comment": "this is only for accessing trading platform mostly via websockets",
    }


@app.post("/experiment/start")
async def start_experiment(
    params: TradingParameters, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_admin_user)
):
    trader_manager = TraderManager(params)
    background_tasks.add_task(trader_manager.launch)
    trader_managers[trader_manager.trading_session.id] = trader_manager

    return {
        "status": "success",
        "message": "New experiment started",
        "data": {
            "trading_session_uuid": trader_manager.trading_session.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": [t.id for t in trader_manager.human_traders],
        },
    }


async def find_or_create_session_and_assign_trader(uid):
    global persistent_settings
    try:
        available_session = next((s for s in trader_managers.values() if len(s.human_traders) < s.params.num_human_traders), None)
        
        if available_session is None:
            params = TradingParameters.from_dict(persistent_settings)
            new_trader_manager = TraderManager(params)
            trader_managers[new_trader_manager.trading_session.id] = new_trader_manager
            available_session = new_trader_manager
        
        trader_id = await available_session.add_human_trader(uid)
        session_id = available_session.trading_session.id
        
        trader_to_session_lookup[trader_id] = session_id
        
        return session_id, trader_id
    except Exception as e:
        raise


async def send_to_frontend(websocket: WebSocket, trader_manager):
    while True:
        trading_session = trader_manager.trading_session
        time_update = {
            "type": "time_update",
            "data": {
                "current_time": trading_session.current_time.isoformat(),
                "is_trading_started": trading_session.trading_started,
                "remaining_time": (
                    trading_session.start_time
                    + timedelta(minutes=trading_session.duration)
                    - trading_session.current_time
                ).total_seconds()
                if trading_session.trading_started
                else None,
                "current_human_traders": len(trader_manager.human_traders),
                "expected_human_traders": trader_manager.params.num_human_traders,
            },
        }
        await websocket.send_json(time_update)
        await asyncio.sleep(1)

async def receive_from_frontend(websocket: WebSocket, trader):
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            parsed_message = json.loads(message)
            await trader.on_message_from_client(message)
        except asyncio.TimeoutError:
            pass
        except WebSocketDisconnect:
            return
        except json.JSONDecodeError:
            pass
        except Exception as e:
            return

@app.get("/session_metrics")
async def get_session_metrics(trader_id: str, session_id: str, current_user: dict = Depends(get_current_user)):
    if trader_id != f"HUMAN_{current_user['uid']}":
        raise HTTPException(status_code=403, detail="Unauthorized access to trader data")
    
    log_file_path = f"logs/{session_id}_trading.log"
    
    try:
        processed_data = process_log_file(log_file_path)
        
        output = io.StringIO()
        write_to_csv(processed_data, output)
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}_trader_{trader_id}_metrics.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing session metrics")


@app.websocket("/trader/{trader_id}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_id: str):
    await websocket.accept()
    token = await websocket.receive_text()
    decoded_token = auth.verify_id_token(token)
    
    trader_manager = get_manager_by_trader(trader_id)
    if not trader_manager:
        await websocket.send_json({"status": "error", "message": "Trader not found", "data": {}})
        await websocket.close()
        return

    trader = trader_manager.get_trader(trader_id)
    await trader.connect_to_socket(websocket)
    
    try:
        send_task = asyncio.create_task(send_to_frontend(websocket, trader_manager))
        receive_task = asyncio.create_task(receive_from_frontend(websocket, trader))
        
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        pass
    finally:
        await trader_manager.cleanup()


current_dir = Path(__file__).resolve().parent
ROOT_DIR = current_dir.parent / "logs"

@app.get("/files")
async def list_files(
    path: str = Query("", description="Relative path to browse")
):
    """
    Endpoint to list files and directories.
    """
    try:
        full_path = (ROOT_DIR / path).resolve()
        
        print(f"Requested path: {path}")
        print(f"Full path: {full_path}")
        print(f"ROOT_DIR: {ROOT_DIR}")
        
        # Ensure the path is within the allowed directory
        if not full_path.is_relative_to(ROOT_DIR):
            print(f"Access denied: {full_path} is not relative to {ROOT_DIR}")
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.exists():
            print(f"Path not found: {full_path}")
            raise HTTPException(status_code=404, detail=f"Path not found: {full_path}")
        
        if full_path.is_file():
            return {"type": "file", "name": full_path.name}
        
        files = []
        directories = []
        
        for item in full_path.iterdir():
            if item.is_file():
                files.append({"type": "file", "name": item.name})
            elif item.is_dir():
                directories.append({"type": "directory", "name": item.name})
        
        return {
            "current_path": str(full_path.relative_to(ROOT_DIR)),
            "parent_path": str(full_path.parent.relative_to(ROOT_DIR)) if full_path != ROOT_DIR else None,
            "directories": directories,
            "files": files
        }
    except Exception as e:
        print(f"Error in list_files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    """
    Endpoint to retrieve files.
    """
    try:
        full_path = (ROOT_DIR / file_path).resolve()
        
        print(f"Requested file: {file_path}")
        print(f"Full path: {full_path}")
        
        # Ensure the file is within the allowed directory
        if not full_path.is_relative_to(ROOT_DIR):
            print(f"Access denied: {full_path} is not relative to {ROOT_DIR}")
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.is_file():
            print(f"File not found: {full_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
        
        return FileResponse(full_path)
    except Exception as e:
        print(f"Error in get_file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/files/{file_path:path}")
async def delete_file(file_path: str):
    """
    Endpoint to delete files.
    """
    try:
        full_path = (ROOT_DIR / file_path).resolve()
        
        print(f"Requested file deletion: {file_path}")
        print(f"Full path: {full_path}")
        
        # Ensure the file is within the allowed directory
        if not full_path.is_relative_to(ROOT_DIR):
            print(f"Access denied: {full_path} is not relative to {ROOT_DIR}")
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.is_file():
            print(f"File not found: {full_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
        
        full_path.unlink()
        return {"status": "success", "message": f"File {file_path} deleted successfully"}
    except Exception as e:
        print(f"Error in delete_file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")