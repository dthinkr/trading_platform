import threading

import uvicorn
from fastapi import FastAPI

from api.endpoints import app

from . import load_config

CONFIG = load_config()


class CustomUvicornServer(uvicorn.Server):
    def install_signal_handlers(self: uvicorn.Server) -> None:
        pass  # prevents default signal handlers


def run_server(port: int) -> None:
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="info")
    server = CustomUvicornServer(config)
    server.run()


def stop_servers(servers: list[CustomUvicornServer]) -> None:
    for server in servers:
        server.should_exit = True


def start_servers(number_of_servers: int, starting_port: int):
    servers = []
    threads = []
    for i in range(number_of_servers):
        port = starting_port + i
        server = CustomUvicornServer(
            config=uvicorn.Config(
                app=app, host="127.0.0.1", port=port, log_level="info"
            )
        )
        servers.append(server)
        thread = threading.Thread(target=server.run)
        threads.append(thread)
        thread.start()

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("Shutting down servers...")
        stop_servers(servers)
        for thread in threads:
            thread.join()


if __name__ == "__main__":
    start_servers(CONFIG.NUM_SERVERS, CONFIG.UVICORN_STARTING_PORT)
