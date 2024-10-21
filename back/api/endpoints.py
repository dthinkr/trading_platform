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
from .auth import get_current_user, get_current_admin_user, get_firebase_auth, extract_gmail_username, is_user_registered, is_user_admin, update_google_form_id, custom_verify_id_token
from .calculate_metrics import process_log_file, write_to_csv
from .logfiles_analysis import order_book_contruction
from firebase_admin import auth
import secrets
import traceback
import json
from pydantic import BaseModel
import os
from fastapi import HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List
from .google_sheet_auth import update_form_id, get_registered_users
import zipfile
import shutil
from collections import defaultdict
import time
import jwt

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

active_users = defaultdict(set)  # Maps session_id to set of active usernames
user_sessions = {}  # Maps username to their current session_id

# Add this near the top of the file, with other global variables
user_historical_sessions = defaultdict(set)

def get_historical_sessions_count(username):
    return len(user_historical_sessions[username])

def record_session_for_user(username, session_id):
    user_historical_sessions[username].add(session_id)

class PersistentSettings(BaseModel):
    settings: dict

@app.post("/admin/update_persistent_settings")
async def update_persistent_settings(settings: PersistentSettings):
    global persistent_settings
    if 'num_human_traders' in settings.settings and 'human_goal_amount' in settings.settings:
        num_traders = int(settings.settings['num_human_traders'])
        goal_amount = int(settings.settings['human_goal_amount'])
        settings.settings['human_goals'] = TradingParameters.generate_human_goals(num_traders, goal_amount)
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
        
        # Add clock_skew_seconds parameter here as well
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        email = decoded_token['email']
        
        form_id = TradingParameters().google_form_id
        if not is_user_registered(email, form_id):
            raise HTTPException(status_code=403, detail="User not registered in the study")
        
        gmail_username = extract_gmail_username(email)
        
        # Check if the user is an admin
        is_admin = is_user_admin(email)
        
        # Check if the user has exceeded the maximum number of historical sessions (skip for admins)
        if not is_admin:
            historical_sessions_count = get_historical_sessions_count(gmail_username)
            if historical_sessions_count >= persistent_settings.get('max_sessions_per_human', 4):
                raise HTTPException(status_code=403, detail="Maximum number of allowed sessions reached for this user")
        
        session_id, trader_id = await find_or_create_session_and_assign_trader(gmail_username)
        
        # Add user to active users for this session
        active_users[session_id].add(gmail_username)
        user_sessions[gmail_username] = session_id
        
        # Record this session in the user's historical sessions
        record_session_for_user(gmail_username, session_id)
        
        return {
            "status": "success",
            "message": "Login successful and trader assigned",
            "data": {
                "username": email,
                "is_admin": is_admin,
                "session_id": session_id,
                "trader_id": trader_id
            }
        }
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/admin/login")
async def admin_login(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    try:
        token = auth_header.split('Bearer ')[1]
        
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        email = decoded_token['email']
        
        if not is_user_admin(email):
            raise HTTPException(status_code=403, detail="User does not have admin privileges")
        
        return {
            "status": "success",
            "message": "Admin login successful",
            "data": {
                "username": email,
                "is_admin": True
            }
        }
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admin login failed: {str(e)}")

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
        merged_params = TradingParameters(**persistent_settings)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    gmail_username = current_user['gmail_username']
    
    try:
        trader_id = f"HUMAN_{gmail_username}"
        session_id = trader_to_session_lookup.get(trader_id)
        
        if not session_id:
            raise HTTPException(status_code=404, detail="No active session found for this user")
        
        trader_manager = trader_managers[session_id]
        
        trader_manager.params = merged_params
        
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
        raise HTTPException(status_code=500, detail=f"Error retrieving trading session info: {str(e)}")
        
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
async def get_trader_info(trader_id: str):
    print(f"Accessing trader info for trader_id: {trader_id}")

    trader_manager = get_manager_by_trader(trader_id)
    if not trader_manager:
        print(f"Trader manager not found for trader_id: {trader_id}")
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

    # Get the session ID for this trader
    session_id = trader_to_session_lookup.get(trader_id)
    
    # Construct the log file path
    log_file_path = os.path.join("logs", f"{session_id}_trading.log")
    
    # Get the order book metrics
    try:
        order_book_metrics = order_book_contruction(log_file_path)
        
        # Extract the specific trader's metrics
        trader_specific_metrics = order_book_metrics.get(f"'{trader_id}'", {})
        
        # Remove the trader-specific metrics from the general metrics
        general_metrics = {k: v for k, v in order_book_metrics.items() if k != f"'{trader_id}'"}
    except Exception as e:
        general_metrics = {"error": "Unable to process log file"}
        trader_specific_metrics = {}

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
            "all_attributes": serializable_attributes,
            "order_book_metrics": general_metrics,
            "trader_specific_metrics": trader_specific_metrics
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


async def find_or_create_session_and_assign_trader(gmail_username):
    global persistent_settings
    try:
        available_session = next((s for s in trader_managers.values() if len(s.human_traders) < s.params.num_human_traders), None)
        
        if available_session is None:
            params = TradingParameters(**persistent_settings)
            new_trader_manager = TraderManager(params)
            trader_managers[new_trader_manager.trading_session.id] = new_trader_manager
            available_session = new_trader_manager
        
        trader_id = await available_session.add_human_trader(gmail_username)
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
    if trader_id != f"HUMAN_{current_user['gmail_username']}":
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
    try:
        decoded_token = custom_verify_id_token(token)  # Remove any clock_skew_seconds parameter here
        email = decoded_token['email']
        gmail_username = extract_gmail_username(email)
        
        current_time = int(time.time())
        token_issued_at = decoded_token.get('iat', 0)
        token_expiry = decoded_token.get('exp', 0)
        
        trader_manager = get_manager_by_trader(trader_id)
        if not trader_manager:
            await websocket.send_json({"status": "error", "message": "Trader not found", "data": {}})
            await websocket.close()
            return

        trader = trader_manager.get_trader(trader_id)
        
        # Remove the user from the active users list when they connect
        # This ensures that if they're reconnecting (e.g., after a refresh), they're not counted twice
        session_id = trader_to_session_lookup.get(trader_id)
        if session_id and gmail_username in active_users[session_id]:
            active_users[session_id].remove(gmail_username)
        
        # Add the user back to the active users list
        if session_id:
            active_users[session_id].add(gmail_username)
        user_sessions[gmail_username] = session_id
        
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
            
        except (asyncio.CancelledError, WebSocketDisconnect):
            pass
        except Exception:
            pass
        finally:
            # Remove the user from the active users list when they disconnect
            if session_id and gmail_username in active_users[session_id]:
                active_users[session_id].remove(gmail_username)
            if gmail_username in user_sessions:
                del user_sessions[gmail_username]

    except jwt.InvalidTokenError as e:
        await websocket.send_json({"status": "error", "message": f"Invalid token: {str(e)}", "data": {}})
        await websocket.close()
        return
    except Exception as e:
        await websocket.send_json({"status": "error", "message": f"Unexpected error: {str(e)}", "data": {}})
        await websocket.close()
        return

current_dir = Path(__file__).resolve().parent
ROOT_DIR = current_dir.parent / "logs"
print(f"ROOT_DIR is set to: {ROOT_DIR}")

@app.get("/files")
async def list_files(
    path: str = Query("", description="Relative path to browse")
):
    try:
        full_path = (ROOT_DIR / path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.exists():
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    try:
        full_path = (ROOT_DIR / file_path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
        
        return FileResponse(full_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/trading/start")
async def start_trading_session(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    session_id = trader_to_session_lookup.get(trader_id)
    
    if not session_id:
        raise HTTPException(status_code=404, detail="No active session found for this user")
    
    trader_manager = trader_managers[session_id]
    
    background_tasks.add_task(trader_manager.launch)
    
    return {
        "status": "success",
        "message": "Trading session started",
        "data": {
            "trading_session_uuid": session_id,
        }
    }

@app.post("/admin/update_google_form_id")
async def update_google_form_id_endpoint(new_form_id: str, current_user: dict = Depends(get_current_admin_user)):
    params = TradingParameters()
    params.google_form_id = new_form_id
    update_form_id(new_form_id)
    return {"status": "success", "message": "Google Form ID updated successfully"}

@app.get("/admin/refresh_registered_users")
async def refresh_registered_users(current_user: dict = Depends(get_current_admin_user)):
    get_registered_users(force_update=True)
    return {"status": "success", "message": "Registered users refreshed"}

# Add a background task to periodically update registered users
async def periodic_update_registered_users():
    while True:
        form_id = TradingParameters().google_form_id
        get_registered_users(force_update=True, form_id=form_id)
        await asyncio.sleep(300)

async def periodic_time_offset_calculation():
    while True:
        # Remove the calculate_time_offset() call
        await asyncio.sleep(3600)  # Sleep for an hour

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_update_registered_users())
    asyncio.create_task(periodic_time_offset_calculation())

@app.get("/files/download/all")
async def download_all_files():
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file in ROOT_DIR.glob('*'):
                if file.is_file():
                    zip_file.write(file, file.name)
        
        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=all_log_files.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Add a new endpoint to handle user logout
@app.post("/user/logout")
async def user_logout(current_user: dict = Depends(get_current_user)):
    gmail_username = current_user['gmail_username']
    if gmail_username in user_sessions:
        session_id = user_sessions[gmail_username]
        active_users[session_id].remove(gmail_username)
        del user_sessions[gmail_username]
        if not active_users[session_id]:
            del active_users[session_id]
        return {"status": "success", "message": "User logged out successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found in any active session")

# Modify the cleanup function to remove users from active sessions
async def cleanup(session_id: str):
    if session_id in active_users:
        for username in active_users[session_id]:
            if username in user_sessions:
                del user_sessions[username]
        del active_users[session_id]
    # ... (rest of the cleanup logic)







