import asyncio
import datetime
import json
from typing import Dict, List
import os
from SALib.sample import sobol
from prefect import flow, get_run_logger, task
from .utilities import load_config
import fcntl
import requests
import itertools

CONFIG = load_config()
file_name = (
    f"trader_data_mapping_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)
file_path = os.path.join(CONFIG.DATA_DIR, file_name)


@task
def write_to_json_file(
    session_id: str,
    trader_data: Dict,
    unscaled_data: Dict = None,
    sobol_problem: Dict = None,
    order: int = None,
) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    if not os.path.exists(file_path):
        initial_data = {"sobol_problem": sobol_problem, "sessions": {}}
        with open(file_path, "w") as f:
            json.dump(initial_data, f, indent=2)

    with open(file_path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            data = json.load(f)
            if session_id != "initial":
                data["sessions"][session_id] = {
                    "order": order,
                    "scaled": trader_data,
                    "unscaled": unscaled_data,
                }
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def create_trading_session(trader_data: Dict, port: int) -> Dict:
    """Initiate a trading session with the given trader data on a specific port."""
    url = f"http://localhost:{port}/trading/initiate"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=trader_data, headers=headers)
    return response.json()


@task
async def create_and_wait_session(
    trader_data: Dict, unscaled_data: Dict, port: int, order: int
) -> None:
    session_info = create_trading_session(trader_data, port)
    session_id = session_info.get("data", {}).get("trading_session_uuid")
    simulation_length = trader_data.get("trading_day_duration", 1)
    buffer_time = 0.05
    total_wait_time = (simulation_length + buffer_time) * 60
    await asyncio.sleep(total_wait_time)
    write_to_json_file.fn(session_id, trader_data, unscaled_data, order=order)


async def handle_server_sessions(
    batch: List[Dict], unscaled_batch: List[Dict], port: int, start_order: int
):
    tasks = []
    for i, (trader_data, unscaled_data) in enumerate(zip(batch, unscaled_batch)):
        task = asyncio.create_task(
            create_and_wait_session(trader_data, unscaled_data, port, start_order + i)
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


def generate_sobol_samples(problem, N):
    return sobol.sample(problem, N)


@flow
async def run_trading_sessions(params: List[Dict], unscaled_params: List[Dict]) -> None:
    num_servers = CONFIG.NUM_SERVERS
    total_sessions = len(params)

    # ordering for all sessions beforehand
    all_orders = list(range(total_sessions))

    batches = [params[i::num_servers] for i in range(num_servers)]
    unscaled_batches = [unscaled_params[i::num_servers] for i in range(num_servers)]
    order_batches = [all_orders[i::num_servers] for i in range(num_servers)]

    get_run_logger().critical(
        f"Running {total_sessions} trading sessions on {num_servers} servers"
    )
    tasks = []
    for i, (batch, unscaled_batch, order_batch) in enumerate(
        zip(batches, unscaled_batches, order_batches)
    ):
        port = CONFIG.UVICORN_STARTING_PORT + i
        task = asyncio.create_task(
            handle_server_sessions(batch, unscaled_batch, port, order_batch)
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


async def handle_server_sessions(
    batch: List[Dict], unscaled_batch: List[Dict], port: int, orders: List[int]
):
    tasks = []
    for trader_data, unscaled_data, order in zip(batch, unscaled_batch, orders):
        task = asyncio.create_task(
            create_and_wait_session(trader_data, unscaled_data, port, order)
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


def generate_parameters(bounds):
    if all(isinstance(b, list) for b in bounds.values()):
        keys = list(bounds.keys())
        values_product = list(itertools.product(*bounds.values()))
        params = [
            {key: value for key, value in zip(keys, values)}
            for values in values_product
        ]
        problem = None
    else:
        problem = {
            "num_vars": len(bounds),
            "names": list(bounds.keys()),
            "bounds": [bounds[name] for name in bounds.keys()],
        }
        N = 2**CONFIG.RESOLUTION
        param_values = generate_sobol_samples(problem, N)
        params = []
        for values in param_values:
            param_dict = {}
            for name, value in zip(problem["names"], values):
                if name == "informed_trade_direction":
                    param_dict[name] = "buy" if round(value) == 1 else "sell"
                elif isinstance(bounds[name][0], int) and isinstance(
                    bounds[name][1], int
                ):
                    param_dict[name] = int(round(value))
                else:
                    param_dict[name] = value
            params.append(param_dict)

    return params, problem


def run_evaluation():
    bounds = CONFIG.BOUNDS
    params, problem = generate_parameters(bounds)

    unscaled_params = [
        {name: param[name] for name in bounds.keys()} for param in params
    ]

    write_to_json_file.fn("initial", {}, None, problem)
    asyncio.run(run_trading_sessions(params, unscaled_params))


if __name__ == "__main__":
    run_evaluation()
