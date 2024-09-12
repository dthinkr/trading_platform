import asyncio
import io
from datetime import timedelta

from fastapi import (
    FastAPI,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
    BackgroundTasks,
    Depends,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_400_BAD_REQUEST
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pymongo import MongoClient
import polars as pl

from core.trader_manager import TraderManager
from core.data_models import TraderCreationData, UserRegistration
from utils import setup_custom_logger
from .calculate_metrics import get_data_from_mongodb, process_session, calculate_end_of_run_metrics
import traceback

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

# In-memory user store (replace with database in production)
users = {
    "admin": {"password": "admin123", "is_admin": True},
    "user1": {"password": "password1", "is_admin": False},
    "user2": {"password": "password2", "is_admin": False}
}

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    if username in users and users[username]["password"] == password:
        return username
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

@app.post("/login")
async def login(username: str = Depends(authenticate)):
    return {
        "status": "success",
        "message": "Login successful",
        "data": {
            "username": username,
            "is_admin": users[username]["is_admin"]
        }
    }

@app.post("/register")
async def register(user: UserRegistration):
    if user.username in users:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    users[user.username] = {"password": user.password, "is_admin": False}
    return {
        "status": "success",
        "message": "User registered successfully",
        "data": {
            "username": user.username,
            "is_admin": False
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.get("/traders/defaults")
async def get_trader_defaults():
    schema = TraderCreationData.model_json_schema()
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
    params: TraderCreationData, background_tasks: BackgroundTasks
):
    trader_manager = TraderManager(params)
    background_tasks.add_task(trader_manager.launch)
    trader_managers[trader_manager.trading_session.id] = trader_manager
    new_traders = list(trader_manager.traders.keys())

    for t in new_traders:
        trader_to_session_lookup[t] = trader_manager.trading_session.id

    return {
        "status": "success",
        "message": "New trading session created",
        "data": {
            "trading_session_uuid": trader_manager.trading_session.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": [t.id for t in trader_manager.human_traders],
        },
    }


def get_manager_by_trader(trader_uuid: str):
    if trader_uuid not in trader_to_session_lookup.keys():
        return None
    trading_session_id = trader_to_session_lookup[trader_uuid]
    return trader_managers[trading_session_id]


@app.get("/trader/{trader_uuid}")
async def get_trader(trader_uuid: str):
    trader_manager = get_manager_by_trader(trader_uuid)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader = trader_manager.traders.get(trader_uuid)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader_data = trader.get_trader_params_as_dict()
    data = trader_manager.get_params()
    data["goal"] = trader_data["goal"]
    return {"status": "success", "message": "Trader found", "data": data}


@app.get("/trader_info/{trader_uuid}")
async def get_trader_info(trader_uuid: str):
    trader_manager = get_manager_by_trader(trader_uuid)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = trader_manager.get_trader(trader_uuid)
    return {
        "status": "success",
        "message": "Trader found",
        "data": {
            "cash": trader.cash,
            "shares": trader.shares,
            "orders": trader.orders,
            "delta_cash": trader.delta_cash,
            "initial_cash": trader.initial_cash,
            "initial_shares": trader.initial_shares,
        },
    }


@app.get("/trading_session/{trading_session_id}")
async def get_trading_session(trading_session_id: str):
    trader_manager = trader_managers.get(trading_session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trading session not found")

    return {
        "status": "found",
        "data": {
            "trading_session_uuid": trader_manager.trading_session.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": [
                t.get_trader_params_as_dict() for t in trader_manager.human_traders
            ],
        },
    }


@app.websocket("/trader/{trader_uuid}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_uuid: str):
    await websocket.accept()

    trader_manager = get_manager_by_trader(trader_uuid)
    if not trader_manager:
        await websocket.send_json(
            {"status": "error", "message": "Trader not found", "data": {}}
        )
        await websocket.close()
        return

    trader = trader_manager.get_trader(trader_uuid)
    await trader.connect_to_socket(websocket)

    logger.info(f"Trader {trader_uuid} connected to websocket")

    try:
        while True:
            await websocket.send_json(
                {
                    "type": "time_update",
                    "data": {
                        "current_time": trader_manager.trading_session.current_time.isoformat(),
                        "is_trading_started": trader_manager.trading_session.trading_started,
                        "remaining_time": (
                            trader_manager.trading_session.start_time
                            + timedelta(minutes=trader_manager.trading_session.duration)
                            - trader_manager.trading_session.current_time
                        ).total_seconds()
                        if trader_manager.trading_session.trading_started
                        else None,
                    },
                }
            )
            await asyncio.sleep(1)

            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                await trader.on_message_from_client(message)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        logger.critical(f"Trader {trader_uuid} disconnected")
    except asyncio.CancelledError:
        logger.warning("Task cancelled")
        await trader_manager.cleanup()


@app.get("/traders/list")
async def list_traders():
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
    params: TraderCreationData, background_tasks: BackgroundTasks
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
async def get_experiment_status(trading_session_id: str):
    trader_manager = trader_managers.get(trading_session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trading session not found")

    is_finished = trader_manager.trading_session.is_finished

    return {
        "status": "success",
        "data": {"trading_session_id": trading_session_id, "is_finished": is_finished},
    }


@app.get("/experiment/time_series_metrics/{trading_session_id}")
async def get_time_series_metrics(trading_session_id: str):
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
async def get_end_metrics(trading_session_id: str):
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