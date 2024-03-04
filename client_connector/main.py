import asyncio

from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect, BackgroundTasks

from fastapi.middleware.cors import CORSMiddleware
from client_connector.trader_manager import TraderManager
from structures import TraderCreationData, TraderManagerParams

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
trader_manager: TraderManager = None


@app.get("/traders/defaults")
async def get_trader_defaults():
    # Get the schema of the model
    schema = TraderCreationData.schema()

    # Extract default values from the schema
    defaults = {field: props.get("default") for field, props in schema.get("properties", {}).items() if
                "default" in props}

    return {
        "status": "success",
        "data": defaults
    }


@app.post("/trading/initiate")
async def create_trading_session(params: TraderManagerParams, background_tasks: BackgroundTasks):
    global trader_manager
    trader_manager = TraderManager({
        "n_noise_traders": params.n_noise_traders,
        "n_human_traders": params.n_human_traders,
        "activity_frequency": params.activity_frequency
    })

    background_tasks.add_task(trader_manager.launch)
    return {
        "status": "success",
        "message": "New trader created",
        "data": {"trading_session_uuid": trader_manager.trading_session.id,
                 "traders": list(trader_manager.traders.keys()),
                 "human_traders": [t.id for t in trader_manager.human_traders],
                 }
    }

@app.websocket("/trader/{trader_uuid}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_uuid: str):
    await websocket.accept()

    global trader_manager
    if trader_manager is None or not trader_manager.exists(trader_uuid):
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
