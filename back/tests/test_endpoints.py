import pytest
from fastapi.testclient import TestClient
from api.endpoints import app
from core.data_models import TraderCreationData
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
            self.is_finished = False

    class MockTrader:
        def __init__(self):
            self.id = "mock-trader-id"
            self.cash = 1000
            self.shares = 100
            self.orders = []
            self.delta_cash = 0
            self.initial_cash = 1000
            self.initial_shares = 100

        def get_trader_params_as_dict(self):
            return {"goal": "mock_goal", "id": "mock-trader-id", "type": "HUMAN"}

        async def connect_to_socket(self, websocket):
            pass

        async def on_message_from_client(self, message):
            pass

    class MockTraderManager:
        def __init__(self):
            self.trading_session = MockTradingSession()
            self.traders = {"mock-trader-id": MockTrader()}
            self.human_traders = [MockTrader()]

        def get_trader(self, uuid):
            return self.traders.get(uuid)

        def get_params(self):
            return {}

        async def launch(self):
            pass

        async def cleanup(self):
            pass

    mock = MockTraderManager()
    monkeypatch.setattr("api.endpoints.TraderManager", lambda *args, **kwargs: mock)
    monkeypatch.setattr("api.endpoints.trader_managers", {"mock-session-id": mock})
    monkeypatch.setattr(
        "api.endpoints.trader_to_session_lookup",
        {"mock-trader-id": "mock-session-id"},
    )
    monkeypatch.setattr(
        "api.endpoints.get_manager_by_trader",
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

def test_create_trading_session(client, mock_trader_manager):
    test_data = TraderCreationData(num_human_traders=2, trading_day_duration=10)
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

def test_login(client):
    response = client.post("/login", auth=("admin", "admin123"))
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["is_admin"] == True

def test_register(client):
    response = client.post("/register", json={"username": "newuser", "password": "newpass"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["username"] == "newuser"

def test_experiment_start(client, mock_trader_manager):
    test_data = TraderCreationData(num_human_traders=2, trading_day_duration=10)
    response = client.post("/experiment/start", json=test_data.model_dump())
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "trading_session_uuid" in response.json()["data"]

def test_experiment_status(client, mock_trader_manager):
    response = client.get("/experiment/status/mock-session-id")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "is_finished" in response.json()["data"]

# Note: The time_series_metrics and end_metrics endpoints are not tested here
# as they require more complex setup with MongoDB. You might want to mock these
# or set up a test database for more comprehensive testing.
