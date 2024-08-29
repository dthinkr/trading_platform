import pytest
from fastapi.testclient import TestClient
from client_connector.main import app
from structures import TraderCreationData
from datetime import datetime, timedelta
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_trader_manager(monkeypatch):
    class MockTradingSession:
        def __init__(self):
            self.id = "mock-session-id"
            self.current_time = datetime.now()
            self.trading_started = True
            self.start_time = self.current_time - timedelta(minutes=5)
            self.duration = 30

    class MockTrader:
        def __init__(self):
            self.cash = 1000
            self.shares = 100
            self.orders = []
            self.delta_cash = 0
            self.initial_cash = 1000
            self.initial_shares = 100

        def get_trader_params_as_dict(self):
            return {"goal": "mock_goal"}

        async def connect_to_socket(self, websocket):
            pass

        async def on_message_from_client(self, message):
            pass

    class MockTraderManager:
        def __init__(self):
            self.trading_session = MockTradingSession()
            self.traders = {"mock-trader-id": MockTrader()}
            self.human_traders = [
                type(
                    "obj",
                    (object,),
                    {
                        "id": "mock-human-trader-id",
                        "get_trader_params_as_dict": lambda: {},
                    },
                )
            ]

        def get_trader(self, uuid):
            return self.traders.get(uuid)

        def get_params(self):
            return {}

        def launch(self):
            pass

        async def cleanup(self):
            pass

    mock = MockTraderManager()
    monkeypatch.setattr(
        "client_connector.main.TraderManager", lambda *args, **kwargs: mock
    )
    monkeypatch.setattr("client_connector.main.trader_manager", mock)
    monkeypatch.setattr(
        "client_connector.main.trader_managers", {"mock-session-id": mock}
    )
    monkeypatch.setattr(
        "client_connector.main.trader_to_session_lookup",
        {"mock-trader-id": "mock-session-id"},
    )
    monkeypatch.setattr(
        "client_connector.main.get_manager_by_trader",
        lambda uuid: mock if uuid == "mock-trader-id" else None,
    )
    return mock


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "trading is active",
        "comment": "this is only for accessing trading platform mostly via websockets",
    }


def test_traders_defaults(client):
    response = client.get("/traders/defaults")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_traders_list(client, mock_trader_manager):
    response = client.get("/traders/list")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "List of traders"


def test_create_trading_session(client, mock_trader_manager):
    test_data = TraderCreationData(num_traders=2, duration=10)
    response = client.post("/trading/initiate", json=test_data.model_dump())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "trading_session_uuid" in response.json()["data"]


@pytest.mark.parametrize(
    "endpoint,uuid_key",
    [
        ("/trader/{uuid}", "trader_uuid"),
        ("/trader_info/{uuid}", "trader_uuid"),
        ("/trading_session/{uuid}", "trading_session_id"),
    ],
)
def test_get_endpoints(client, mock_trader_manager, endpoint, uuid_key):
    mock_uuid = "mock-trader-id" if uuid_key == "trader_uuid" else "mock-session-id"
    response = client.get(endpoint.format(uuid=mock_uuid))
    assert response.status_code == 200
    assert response.json()["status"] in ["success", "found"]


def test_websocket_endpoint(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Hello")
            data = websocket.receive_text()
            assert data == "Message text was: Hello"


def test_websocket_trader_endpoint(client, mock_trader_manager):
    trader_uuid = "mock-trader-id"
    with client.websocket_connect(f"/trader/{trader_uuid}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "time_update"
        assert "current_time" in data["data"]
        # Force close the connection to avoid hanging
        websocket.close()


def test_error_handling(client):
    response = client.get("/trader/non-existent-uuid")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trader not found"
