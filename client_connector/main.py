import asyncio

from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect, BackgroundTasks
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from client_connector.trader_manager import TraderManager
from structures import TraderCreationData
from fastapi.responses import JSONResponse
from typing import List
from pprint import pprint
import logging

logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# TODO: for now we keep it in memory, but we may want to persist it in a database
trader_managers = {}
trader_to_session_lookup = {}
trader_manager: TraderManager = None


@app.get("/traders/defaults")
async def get_trader_defaults():
    schema = TraderCreationData.model_json_schema()
    defaults = {field: {"default": props.get("default"), "title": props.get("title"), "type": props.get("type")}
                for field, props in schema.get("properties", {}).items()}

    return JSONResponse(content={
        "status": "success",
        "data": defaults
    })


@app.post("/trading/initiate")
async def create_trading_session(params: TraderCreationData, background_tasks: BackgroundTasks):
    trader_manager = TraderManager(params)

    background_tasks.add_task(trader_manager.launch)
    trader_managers[trader_manager.trading_session.id] = trader_manager
    new_traders = list(trader_manager.traders.keys())

    # loop through the traders and add them to the lookup with values of their session id
    for t in new_traders:
        trader_to_session_lookup[t] = trader_manager.trading_session.id

    return {
        "status": "success",
        "message": "New trading session created",
        "data": {"trading_session_uuid": trader_manager.trading_session.id,
                 "traders": list(trader_manager.traders.keys()),
                 "human_traders": [t.id for t in trader_manager.human_traders],
                 }
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

    return {
        "status": "success",
        "message": "Trader found",
        "data": trader_manager.get_params()
    }


@app.get("/trading_session/{trading_session_id}")
async def get_trading_session(trading_session_id: str):
    trader_manager = trader_managers.get(trading_session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trading session not found")

    return {
        "status": "found",
        "data": {"trading_session_uuid": trader_manager.trading_session.id,
                 "traders": list(trader_manager.traders.keys()),
                 "human_traders": [t.id for t in trader_manager.human_traders],
                 }
    }


@app.websocket("/trader/{trader_uuid}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_uuid: str):
    await websocket.accept()

    trader_manager = get_manager_by_trader(trader_uuid)
    if not trader_manager:
        await websocket.send_json({
            "status": "error",
            "message": "Trader not found",
            "data": {}
        })
        await websocket.close()
        return

    trader = trader_manager.get_trader(trader_uuid)
    trader.connect_to_socket(websocket)
    logger.info(f"Trader {trader_uuid} connected to websocket")
    # Send current status immediately upon new connection
    await websocket.send_json({
        "type": "success",
        "message": "Connected to trader",
        "data": {
            "trader_uuid": trader_uuid,
            "order_book": trader.order_book
        }
    })

    try:
        while True:
            message = await websocket.receive_text()
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning(f"Trader {trader_uuid} disconnected")
                break
            await trader.on_message_from_client(message)
    except WebSocketDisconnect:
        logger.critical(f"Trader {trader_uuid} disconnected")
        pass  # should we something here? not sure, because it can be just an connection interruption
    except asyncio.CancelledError:
        logger.warning("Task cancelled")
        await trader_manager.cleanup()  # This will now cancel all tasks


@app.get("/traders/list")
async def list_traders():
    return {
        "status": "success",
        "message": "List of traders",
        "data": {"traders": list(trader_manager.traders.keys())}
    }


@app.get("/")
async def root():
    return {"status": "trading is active",
            "comment": "this is only for accessing trading platform mostly via websockets"}
