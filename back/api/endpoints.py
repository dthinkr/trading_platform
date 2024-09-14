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
from pymongo import MongoClient
import polars as pl
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder
from core.trader_manager import TraderManager
from core.data_models import TraderType, TradingParameters, UserRegistration
from utils import setup_custom_logger
from .calculate_metrics import get_data_from_mongodb, process_session, calculate_end_of_run_metrics
from .auth import get_current_user, get_current_admin_user, get_firebase_auth
from firebase_admin import auth
import secrets
import logging
import traceback
import json

logger = setup_custom_logger(__name__)

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

MONGODB_HOST = "localhost"
MONGODB_PORT = 27017
DATASET = "trader"
COLLECTION_NAME = "message"

mongo_client = MongoClient(MONGODB_HOST, MONGODB_PORT)
db = mongo_client[DATASET]
collection = db[COLLECTION_NAME]

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
        logger.error(f"ValueError in user_login: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/admin/login")
async def admin_login(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "admin")
    print(credentials.username, credentials.password)
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
async def create_trading_session(
    params: TradingParameters, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)
):
    uid = current_user['uid']
    
    try:
        session_id, trader_id = await find_or_create_session_and_assign_trader(uid)
        
        trader_manager = trader_managers[session_id]
        
        # If this is a new session, launch it
        if len(trader_manager.human_traders) == 1:
            background_tasks.add_task(trader_manager.launch)
        
        return {
            "status": "success",
            "message": "Trader assigned to trading session",
            "data": {
                "trading_session_uuid": session_id,
                "trader_id": trader_id,
                "traders": list(trader_manager.traders.keys()),
                "human_traders": [t.id for t in trader_manager.human_traders],
            },
        }
    except Exception as e:
        logger.error(f"Error in create_trading_session: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error creating or joining trading session")


def get_manager_by_trader(trader_id: str):
    if trader_id not in trader_to_session_lookup.keys():
        print(f"Trader {trader_id} not found in trader_to_session_lookup")
        return None
    trading_session_id = trader_to_session_lookup[trader_id]
    manager = trader_managers[trading_session_id]
    print(f"Retrieved trader manager for {trader_id}: {manager}")
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
            "shares": trader.shares,
            "orders": trader.orders,
            "delta_cash": trader.delta_cash,
            "initial_cash": trader.initial_cash,
            "initial_shares": trader.initial_shares,
            "all_attributes": serializable_attributes
        },
    }
    
    return trader_info

@app.get("/trader/{trader_id}/session")
async def get_trader_session(trader_id: str, current_user: dict = Depends(get_current_user)):
    print(f"Authenticated user accessing session for trader: {trader_id}")
    print(f"Current user data: {current_user}")
    
    session_id = trader_to_session_lookup.get(trader_id)
    if not session_id:
        print(f"No session found for trader: {trader_id}")
        raise HTTPException(status_code=404, detail="No session found for this trader")
    
    trader_manager = trader_managers.get(session_id)
    if not trader_manager:
        print(f"Trader manager not found for session: {session_id}")
        raise HTTPException(status_code=404, detail="Trader manager not found")

    print(f"Found trader manager for session: {session_id}")
    
    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]
    print(f"Human traders data: {human_traders_data}")

    response_data = {
        "status": "success",
        "data": {
            "trading_session_uuid": trader_manager.trading_session.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": human_traders_data,
            "game_params": trader_manager.params.model_dump()
        },
    }
    print(f"Returning response for trader {trader_id}")
    print(f"Response data: {response_data}")
    
    return response_data
    
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
    
    if not trader.trading_system_exchange:
        await trader.connect_to_session(trader_manager.trading_session.id)
    
    await trader.connect_to_socket(websocket)
    
    while True:
        print(f"Sending time update for trader {trader_id}")
        trader_manager = get_manager_by_trader(trader_id)
        trading_session = trader_manager.trading_session
        
        await websocket.send_json(
            {
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
        )
        print(f"Time update sent for trader {trader_id}, is_trading_started: {trading_session.trading_started}")
        await asyncio.sleep(1)

        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            await trader.on_message_from_client(message)
        except asyncio.TimeoutError:
            pass

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


@app.get("/experiment/status/{trading_session_id}")
async def get_experiment_status(trading_session_id: str, current_user: dict = Depends(get_current_user)):
    trader_manager = trader_managers.get(trading_session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trading session not found")

    is_finished = trader_manager.trading_session.is_finished

    return {
        "status": "success",
        "data": {"trading_session_id": trading_session_id, "is_finished": is_finished},
    }


@app.get("/experiment/time_series_metrics/{trading_session_id}")
async def get_time_series_metrics(trading_session_id: str, current_user: dict = Depends(get_current_user)):
    trader_manager = trader_managers.get(trading_session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trading session not found")

    if not trader_manager.trading_session.is_finished:
        raise HTTPException(
            status_code=400, detail="Trading session is not finished yet"
        )

    run_data = get_data_from_mongodb([trading_session_id])
    processed_data = process_session(run_data)
    
    return JSONResponse(content={"status": "success", "data": processed_data})


@app.get("/experiment/end_metrics/{trading_session_id}")
async def get_end_metrics(trading_session_id: str, current_user: dict = Depends(get_current_user)):
    try:
        run_data = get_data_from_mongodb([trading_session_id])
        
        if run_data.is_empty():
            raise HTTPException(
                status_code=404, detail="No data found for this session"
            )

        # Calculate the end-of-run metrics (currently returns an empty dict)
        metrics = calculate_end_of_run_metrics(run_data)

        # Create an empty CSV (you can modify this later to include actual metrics)
        csv_buffer = io.StringIO()
        csv_buffer.write("")  # Write an empty string
        csv_buffer.seek(0)

        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=end_metrics_{trading_session_id}.csv",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        logger.error(f"Error calculating end-of-run metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Error calculating metrics")


async def find_or_create_session_and_assign_trader(uid):
    logger.debug(f"Finding or creating session for uid: {uid}")
    try:
        # Find an available session or create a new one if all are full
        available_session = next((s for s in trader_managers.values() if len(s.human_traders) < s.params.num_human_traders), None)
        
        if available_session is None:
            logger.debug("No available session found, creating a new one")
            params = TradingParameters()
            new_trader_manager = TraderManager(params)
            trader_managers[new_trader_manager.trading_session.id] = new_trader_manager
            available_session = new_trader_manager
        
        logger.debug(f"Assigning trader to session: {available_session.trading_session.id}")
        trader_id = await available_session.add_human_trader(uid)
        session_id = available_session.trading_session.id
        
        trader_to_session_lookup[trader_id] = session_id
        
        logger.debug(f"Trader assigned. Session ID: {session_id}, Trader ID: {trader_id}")
        return session_id, trader_id
    except Exception as e:
        logger.error(f"Error in find_or_create_session_and_assign_trader: {str(e)}")
        logger.error(traceback.format_exc())
        raise