import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import asyncio

from api.endpoints import app, get_manager_by_trader
from core.trader_manager import TraderManager
from fastapi import HTTPException

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_get_current_user():
    async def mock_current_user(request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Invalid authentication method")
        
        # Simulate successful token verification
        return {"uid": "HUMAN_0Jk378svzGQrqPvRYBCdcwqi4ep1", "is_admin": False}
    
    return mock_current_user

@pytest.fixture
def mock_trader_manager():
    mock_manager = MagicMock(spec=TraderManager)
    mock_manager.get_trader.return_value = MagicMock(
        id="HUMAN_0Jk378svzGQrqPvRYBCdcwqi4ep1",
        trader_type="HUMAN",
        cash=1000,
        shares=10,
        initial_cash=1000,
        initial_shares=10,
        goal="MAXIMIZE_PROFIT",
        orders=[],
        delta_cash=0,
        sum_dinv=0,
        get_vwap=MagicMock(return_value=100),
        get_current_pnl=MagicMock(return_value=0)
    )
    return mock_manager

@pytest.fixture
def mock_get_manager_by_trader(mock_trader_manager):
    return MagicMock(return_value=mock_trader_manager)

@pytest.fixture(autouse=True)
def cleanup_event_loop():
    yield
    loop = asyncio.get_event_loop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True))

def test_get_trader_attributes_success(client, mock_get_current_user, mock_get_manager_by_trader):
    with patch("api.auth.get_current_user", mock_get_current_user), \
         patch("api.endpoints.get_manager_by_trader", mock_get_manager_by_trader):
        response = client.get("/trader/HUMAN_0Jk378svzGQrqPvRYBCdcwqi4ep1/attributes", headers={"Authorization": "Bearer test_token"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "data" in response.json()
    assert response.json()["data"]["id"] == "HUMAN_0Jk378svzGQrqPvRYBCdcwqi4ep1"

def test_get_trader_attributes_forbidden(client, mock_get_current_user, mock_get_manager_by_trader):
    async def mock_different_user(request):
        return {"uid": "different_user", "is_admin": False}
    
    with patch("api.auth.get_current_user", mock_different_user), \
         patch("api.endpoints.get_manager_by_trader", mock_get_manager_by_trader):
        response = client.get("/trader/HUMAN_0Jk378svzGQrqPvRYBCdcwqi4ep1/attributes", headers={"Authorization": "Bearer test_token"})
    
    assert response.status_code == 403
    assert "You don't have permission to access this trader's attributes" in response.json()["detail"]

def test_get_trader_attributes_not_found(client, mock_get_current_user):
    with patch("api.auth.get_current_user", mock_get_current_user), \
         patch("api.endpoints.get_manager_by_trader", return_value=None):
        response = client.get("/trader/nonexistent_trader/attributes", headers={"Authorization": "Bearer test_token"})
    
    assert response.status_code == 404
    assert "Trader not found" in response.json()["detail"]