import asyncio

import requests
from uvicorn import Config, Server


async def run_server(port: int) -> None:
    config = Config(
        "client_connector.main:app", host="127.0.0.1", port=port, log_level="info"
    )
    server = Server(config)
    await server.serve()


async def start_servers(number_of_servers: int) -> None:
    base_port = 8000
    tasks = []
    for i in range(number_of_servers):
        port = base_port + i
        task = asyncio.create_task(run_server(port))
        tasks.append(task)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    number_of_servers = 10
    asyncio.run(start_servers(number_of_servers))