import asyncio

from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect, BackgroundTasks
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from client_connector.trader_manager import TraderManager
from structures import TraderCreationData
from fastapi.responses import JSONResponse
from main_platform.custom_logger import setup_custom_logger

from datetime import timedelta

logger = setup_custom_logger(__name__)

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


# for testing if sockets work
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.get("/traders/defaults")
async def get_trader_defaults():
    schema = TraderCreationData.model_json_schema()
    defaults = {field: {"default": props.get("default"), "title": props.get("title"), "type": props.get("type"),
                        "hint": props.get("description")}
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
    trader = trader_manager.traders.get(trader_uuid)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader_data = trader.get_trader_params_as_dict()
    data=trader_manager.get_params()
    data['goal']=trader_data['goal']
    return {
        "status": "success",
        "message": "Trader found",
        "data": data
    }


# let's write a get endpoint for the current information about the trader: inventory, cash, shares, orders
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
            "initial_shares": trader.initial_shares
        }
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
                 "human_traders": [t.get_trader_params_as_dict() for t in trader_manager.human_traders],
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
    await trader.connect_to_socket(websocket)

    logger.info(f"Trader {trader_uuid} connected to websocket")
    
    try:
        while True:
            # Send time update every second
            await websocket.send_json({
                "type": "time_update",
                "data": {
                    "current_time": trader_manager.trading_session.current_time.isoformat(),
                    "is_trading_started": trader_manager.trading_session.trading_started,
                    "remaining_time": (trader_manager.trading_session.start_time + timedelta(minutes=trader_manager.trading_session.duration) - trader_manager.trading_session.current_time).total_seconds() if trader_manager.trading_session.trading_started else None
                }
            })
            await asyncio.sleep(1)  # Wait for 1 second before sending the next update
            
            # Handle incoming messages
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                await trader.on_message_from_client(message)
            except asyncio.TimeoutError:
                pass  # No message received, continue with the loop
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
        "data": {"traders": list(trader_manager.traders.keys())}
    }


@app.get("/")
async def root():
    return {"status": "trading is active",
            "comment": "this is only for accessing trading platform mostly via websockets"}
