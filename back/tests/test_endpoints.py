# import pytest
# from fastapi.testclient import TestClient
# from unittest.mock import patch, MagicMock
# from core.data_models import TradingParameters
# from core.trader_manager import TraderManager
# from api.endpoints import app, find_or_create_session_and_assign_trader, trader_managers
# from firebase_admin import auth

# @pytest.fixture
# def test_client():
#     return TestClient(app)

# @pytest.fixture
# def mock_firebase_auth():
#     with patch('api.auth.auth') as mock_auth:
#         mock_auth.verify_id_token.return_value = {'uid': 'test_uid'}
#         mock_auth.RevokedIdTokenError = Exception
#         yield mock_auth

# @pytest.fixture
# def mock_trader_manager():
#     with patch('api.endpoints.TraderManager') as mock_tm:
#         mock_tm_instance = MagicMock()
#         mock_tm_instance.trading_session.id = 'test_session_id'
#         mock_tm_instance.params.num_human_traders = 2
#         mock_tm_instance.human_traders = []
#         mock_tm_instance.add_human_trader.side_effect = ['HUMAN_uid1', 'HUMAN_uid2', 'HUMAN_uid3', 'HUMAN_uid4', 'HUMAN_uid5']
#         mock_tm.return_value = mock_tm_instance
#         yield mock_tm

# @pytest.fixture
# def mock_get_current_user():
#     with patch('api.auth.get_current_user') as mock:
#         mock.return_value = {'uid': 'test_uid', 'is_admin': False}
#         yield mock

# def test_user_login_new_session(test_client, mock_firebase_auth, mock_trader_manager):
#     response = test_client.post("/user/login", headers={"Authorization": "Bearer test_token"})
#     assert response.status_code == 200
#     assert response.json()['status'] == 'success'
#     assert 'session_id' in response.json()['data']
#     assert 'trader_id' in response.json()['data']

# def test_user_login_existing_session(test_client, mock_firebase_auth, mock_trader_manager):
#     # First login
#     test_client.post("/user/login", headers={"Authorization": "Bearer test_token1"})
    
#     # Second login should join the same session
#     response = test_client.post("/user/login", headers={"Authorization": "Bearer test_token2"})
#     assert response.status_code == 200
#     assert response.json()['status'] == 'success'
#     assert response.json()['data']['session_id'] == 'test_session_id'

# def test_user_login_new_session_when_full(test_client, mock_firebase_auth, mock_trader_manager):
#     # Fill up the first session
#     test_client.post("/user/login", headers={"Authorization": "Bearer test_token1"})
#     test_client.post("/user/login", headers={"Authorization": "Bearer test_token2"})
    
#     # This should create a new session
#     mock_trader_manager.return_value.trading_session.id = 'test_session_id_2'
#     mock_trader_manager.return_value.human_traders = ['HUMAN_uid1', 'HUMAN_uid2']
#     response = test_client.post("/user/login", headers={"Authorization": "Bearer test_token3"})
#     assert response.status_code == 200
#     assert response.json()['data']['session_id'] == 'test_session_id_2'

# def test_find_or_create_session_and_assign_trader(mock_trader_manager):
#     with patch('api.endpoints.trader_managers', {}) as mock_trader_managers:
#         # First trader
#         session_id, trader_id = find_or_create_session_and_assign_trader('uid1')
#         assert session_id == 'test_session_id'
#         assert trader_id == 'HUMAN_uid1'
        
#         # Second trader (same session)
#         session_id, trader_id = find_or_create_session_and_assign_trader('uid2')
#         assert session_id == 'test_session_id'
#         assert trader_id == 'HUMAN_uid2'
        
#         # Third trader (new session)
#         mock_trader_manager.return_value.trading_session.id = 'test_session_id_2'
#         session_id, trader_id = find_or_create_session_and_assign_trader('uid3')
#         assert session_id == 'test_session_id_2'
#         assert trader_id == 'HUMAN_uid3'

# @pytest.mark.asyncio
# async def test_get_trader_session(test_client, mock_firebase_auth, mock_get_current_user):
#     trader_id = 'HUMAN_test_uid'
#     session_id = 'test_session_id'
#     mock_trader_manager = MagicMock()
#     mock_trader_manager.trading_session.id = session_id
#     mock_trader_manager.params.model_dump.return_value = {'param1': 'value1'}
#     mock_trader_manager.human_traders = [MagicMock()]
#     mock_trader_manager.human_traders[0].get_trader_params_as_dict.return_value = {'trader_param': 'value'}
    
#     with patch('api.endpoints.trader_managers', {session_id: mock_trader_manager}), \
#          patch('api.endpoints.trader_to_session_lookup', {trader_id: session_id}):
#         response = test_client.get(f"/trader/{trader_id}/session", headers={"Authorization": "Bearer test_token"})
    
#     assert response.status_code == 200
#     assert response.json()['status'] == 'success'
#     assert response.json()['data']['trading_session_uuid'] == session_id
#     assert 'human_traders' in response.json()['data']
#     assert 'game_params' in response.json()['data']

# @pytest.mark.asyncio
# async def test_create_trading_session(test_client, mock_trader_manager, mock_firebase_auth, mock_get_current_user):
#     params = TradingParameters()
#     response = test_client.post("/experiment/start", 
#                                 json=params.model_dump(),
#                                 headers={"Authorization": "Bearer test_token"})
#     assert response.status_code == 200
#     assert response.json()['status'] == 'success'
#     assert 'trading_session_uuid' in response.json()['data']
#     assert 'traders' in response.json()['data']
#     assert 'human_traders' in response.json()['data']