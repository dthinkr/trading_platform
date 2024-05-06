from fastapi.testclient import TestClient
from client_connector.main import app
import pytest

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "trading is active", "comment": "this is only for accessing trading platform mostly via websockets"}

def test_traders_defaults():
    response = client.get("/traders/defaults")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_create_trading_session():
    test_data = {
        "param1": "value1",
        "param2": "value2"
    }
    response = client.post("/trading/initiate", json=test_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_trader():
    trader_uuid = "existing-trader-uuid"
    response = client.get(f"/trader/{trader_uuid}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_trader_info():
    trader_uuid = "existing-trader-uuid"
    response = client.get(f"/trader_info/{trader_uuid}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_trading_session():
    trading_session_id = "existing-session-id"
    response = client.get(f"/trading_session/{trading_session_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "found"

def test_list_traders():
    response = client.get("/traders/list")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_websocket_endpoint():
    async with client.websocket_connect("/ws") as websocket:
        await websocket.send_text("Hello")
        data = await websocket.receive_text()
        assert data == "Message text was: Hello"

@pytest.mark.asyncio
async def test_websocket_trader_endpoint():
    trader_uuid = "existing-trader-uuid"
    async with client.websocket_connect(f"/trader/{trader_uuid}") as websocket:
        await websocket.send_text("Hello")
        data = await websocket.receive_json()
        assert data["type"] == "success"