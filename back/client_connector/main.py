import asyncio
import io
from datetime import timedelta

from fastapi import (
    FastAPI,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pymongo import MongoClient
import polars as pl

from client_connector.trader_manager import TraderManager
from structures import TraderCreationData
from main_platform.custom_logger import setup_custom_logger
from analysis.record_pm import (
    calculate_time_series_metrics,
    calculate_end_of_run_metrics,
    plot_session_metrics,
)
import traceback

logger = setup_custom_logger(__name__)

app = FastAPI()
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


@app.get("/session_metrics/{id}")
async def get_session_metrics(id: str):
    if id in trader_managers:
        session_id = id
    else:
        session_id = trader_to_session_lookup.get(id)

    if not session_id:
        raise HTTPException(status_code=404, detail="No session found for this ID")

    df = pl.DataFrame(list(collection.find({"trading_session_id": session_id})))

    if df.is_empty():
        raise HTTPException(status_code=404, detail="No data found for this session")

    session_metrics = calculate_time_series_metrics(df)[session_id]

    csv_buffer = io.BytesIO()
    session_metrics.write_csv(csv_buffer)
    csv_buffer.seek(0)

    return StreamingResponse(
        csv_buffer,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=session_metrics_{session_id}.csv",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


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

    return await get_session_metrics(trading_session_id)


@app.get("/experiment/end_metrics/{trading_session_id}")
async def get_end_metrics(trading_session_id: str):
    try:
        # Fetch the data for the specific trading session
        df = pl.DataFrame(
            list(collection.find({"trading_session_id": trading_session_id}))
        )

        if df.is_empty():
            raise HTTPException(
                status_code=404, detail="No data found for this session"
            )

        # Calculate the end-of-run metrics
        metrics = calculate_end_of_run_metrics(df)

        return JSONResponse(content={"status": "success", "data": metrics})
    except Exception as e:
        logger.error(f"Error calculating end-of-run metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Error calculating metrics")


@app.get("/experiment/time_series_plot/{trading_session_id}")
async def get_session_plot(trading_session_id: str):
    try:
        # Fetch the data for the specific trading session
        data = list(collection.find({"trading_session_id": trading_session_id}))

        df = pl.DataFrame(data)

        if df.is_empty():
            raise HTTPException(
                status_code=404, detail="No data found for this session"
            )

        # Calculate time series metrics
        time_series_metrics = calculate_time_series_metrics(df)
        session_metrics = time_series_metrics[trading_session_id]

        # Generate the plot
        svg_string = plot_session_metrics(session_metrics, trading_session_id)

        return Response(content=svg_string, media_type="image/svg+xml")
    except Exception as e:
        error_details = {"error": str(e), "traceback": traceback.format_exc()}
        print(error_details)
        logger.error(f"Error generating session plot: {error_details}")
        raise HTTPException(status_code=500, detail=error_details)
