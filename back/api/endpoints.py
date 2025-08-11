import asyncio
import io
from datetime import timedelta, datetime

# main imports
from fastapi import (
    FastAPI, WebSocket, HTTPException, WebSocketDisconnect, 
    BackgroundTasks, Depends, Request, Response, Query
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.security import HTTPBasic

# our stuff
from core.trader_manager import TraderManager
from core.simple_market_handler import SimpleMarketHandler
from core.data_models import TraderType, TradingParameters, UserRegistration, TraderRole
from .auth import get_current_user, get_current_admin_user, extract_gmail_username, is_user_registered, is_user_admin, custom_verify_id_token
from .prolific_auth import extract_prolific_params, validate_prolific_user, authenticate_prolific_user
from utils.calculate_metrics import process_log_file, write_to_csv
from utils.logfiles_analysis import order_book_contruction, calculate_trader_specific_metrics
from firebase_admin import auth
from utils.websocket_utils import sanitize_websocket_message

# python stuff we need
import json
import os
import csv
import zipfile
from pydantic import BaseModel, ValidationError
from pathlib import Path
from typing import Dict, Any, List
from .google_sheet_auth import get_registered_users

# init fastapi
app = FastAPI()
security = HTTPBasic()

# Global variables


# Initialize with default values from TradingParameters
# Use model_dump() to get a dictionary representation of all parameters
default_params = TradingParameters()
persistent_settings = default_params.model_dump()
accumulated_rewards = {}  # Store accumulated rewards per user

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

# Separate middleware for security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

market_handler = SimpleMarketHandler()
trader_managers = {}

# helper funcs
def get_historical_markets_count(username):
    return len(market_handler.user_historical_markets[username])

def record_market_for_user(username, market_id):
    market_handler.user_historical_markets[username].add(market_id)

class PersistentSettings(BaseModel):
    settings: dict

# Update the persistent settings endpoint
@app.post("/admin/update_persistent_settings")
async def update_persistent_settings(settings: PersistentSettings):
    global persistent_settings  # Only use global when modifying
    
    # Import and set up parameter logger
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()
    
    # Update settings
    persistent_settings = settings.settings
    
    # Log the complete current state
    logger.log_parameter_state(
        current_state=persistent_settings,
        source='admin_update'
    )
    
    return {"status": "success", "message": "Persistent settings updated"}

@app.get("/admin/get_persistent_settings")
async def get_persistent_settings():
    return {"status": "success", "data": persistent_settings}

@app.get("/admin/download_parameter_history")
async def download_parameter_history(current_user: dict = Depends(get_current_admin_user)):
    """Download the parameter history JSON file"""
    param_history_path = Path("logs/parameters/parameter_history.json")
    if not param_history_path.exists():
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Parameter history file not found"}
        )
    
    return FileResponse(
        path=param_history_path,
        filename="parameter_history.json",
        media_type="application/json"
    )



@app.post("/user/login")
async def user_login(request: Request):
    # Check for Prolific parameters first
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        # Use the authenticate_prolific_user function which properly checks credentials
        try:
            prolific_user = await authenticate_prolific_user(request)
            if prolific_user:
                # Use Prolific ID as username
                gmail_username = prolific_user['gmail_username']
                
                # Create parameters
                params = TradingParameters(**(persistent_settings or {}))
                
                # Single call to handle all market/role/goal logic
                market_id, trader_id, role, goal = await market_handler.validate_and_assign_role(
                    gmail_username, 
                    params
                )
                
                # Get the Prolific token to return to the client
                prolific_token = prolific_user.get('prolific_token', '')
                
                print(f"Authenticated Prolific user via params: {gmail_username}")
                
                return {
                    "status": "success",
                    "message": "Prolific login successful and trader assigned",
                    "data": {
                        "trader_id": trader_id,
                        "market_id": market_id,
                        "role": role.value,
                        "goal": goal,
                        "is_admin": False,
                        "is_prolific": True,
                        "prolific_token": prolific_token  # Include the token for future authentication
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Prolific credentials",
                )
        except HTTPException as e:
            # Re-raise the exception from authenticate_prolific_user
            raise e
    
    # If not Prolific, proceed with regular Firebase authentication
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    token = auth_header.split('Bearer ')[1]
    decoded_token = custom_verify_id_token(token)
    email = decoded_token['email']
    gmail_username = extract_gmail_username(email)
    
    # Check registration
    form_id = TradingParameters().google_form_id
    if not is_user_registered(email, form_id):
        raise HTTPException(status_code=403, detail="User not registered in the study")
    
    # Create parameters
    params = TradingParameters(**(persistent_settings or {}))
    
    # Single call to handle all market/role/goal logic
    market_id, trader_id, role, goal = await market_handler.validate_and_assign_role(
        gmail_username, 
        params
    )
    
    return {
        "status": "success",
        "message": "Login successful and trader assigned",
        "data": {
            "username": email,
            "is_admin": is_user_admin(email),
            "market_id": market_id,
            "trader_id": trader_id,
            "role": role,
            "goal": goal
        }
    }

@app.post("/admin/login")
async def admin_login(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    token = auth_header.split('Bearer ')[1]
    decoded_token = custom_verify_id_token(token)
    email = decoded_token['email']
    
    if not is_user_admin(email):
        raise HTTPException(status_code=403, detail="User does not have admin privileges")
    
    return {
        "status": "success",
        "message": "Admin login successful",
        "data": {
            "username": email,
            "is_admin": True
        }
    }

@app.get("/traders/defaults")
async def get_trader_defaults():
    schema = TradingParameters.model_json_schema()
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
async def create_trading_market(background_tasks: BackgroundTasks, request: Request, current_user: dict = Depends(get_current_user)):
    # No need for global here since we're only reading
    try:
        merged_params = TradingParameters(**(persistent_settings or {}))
    except Exception as e:
        merged_params = TradingParameters()
        print(f"Error applying persistent settings: {str(e)}")
    
    # Get trader ID from the current user
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    print(f"Trading/initiate called for user: {gmail_username}, trader_id: {trader_id}, is_prolific: {is_prolific}")
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    if session_status.get("status") == "not_found":
        # User needs to login first to join a session
        raise HTTPException(status_code=404, detail="Please login first to join a trading session")
    
    # If user is in waiting session, return minimal waiting info (no session/market IDs)
    if session_status.get("status") == "waiting":
        response_data = {
            "status": "waiting",
            "message": "Waiting for other traders to join",
            "data": {
                "trader_id": trader_id,
                "num_human_traders": len(merged_params.predefined_goals),
                "isWaitingForOthers": True
            }
        }
        return response_data
    
    # If market is active, get the trader manager using trader ID only
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        # This shouldn't happen if session status is active
        print(f"No trader manager found for {trader_id}")
        raise HTTPException(status_code=404, detail="No active market found for this user")
    
    # Update the manager's parameters with our merged params
    trader_manager.params = merged_params
    
    # Ensure the human trader has a record even if they don't trade
    # This is important for Prolific users who may not actively trade
    if hasattr(trader_manager, 'human_traders'):
        for human_trader in trader_manager.human_traders:
            if human_trader.id == trader_id and hasattr(human_trader, 'handle_TRADING_STARTED'):
                # This will trigger the zero-amount order for record-keeping
                print(f"Ensuring record for human trader: {trader_id}")
    
    response_data = {
        "status": "success",
        "message": "Trading market info retrieved",
        "data": {
            "trader_id": trader_id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": [t.id for t in trader_manager.human_traders],
            "num_human_traders": len(merged_params.predefined_goals),
            "isWaitingForOthers": False
        }
    }
    
    return response_data

def get_manager_by_trader(trader_id: str):
    """Get trader manager for trader ID"""
    if trader_id not in market_handler.trader_to_market_lookup:
        return None
    trading_market_id = market_handler.trader_to_market_lookup[trader_id]
    manager = market_handler.trader_managers.get(trading_market_id)
    return manager



def get_trader_info_with_market_data(trader_manager: TraderManager, trader_id: str) -> Dict[str, Any]:
    try:
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail="Trader not found")

        trader_data = trader.get_trader_params_as_dict()

        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}
            
        gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None
        
        historical_markets_count = len(market_handler.user_historical_markets.get(gmail_username, set()))
        
        params = trader_manager.params.model_dump() if trader_manager.params else {}
        
        admin_users = params.get('admin_users', [])
        is_admin = gmail_username in admin_users if gmail_username else False
        
        trader_data['all_attributes'].update({
            'historical_markets_count': historical_markets_count,
            'is_admin': is_admin,
            'params': params
        })
        
        if 'cash' not in trader_data:
            trader_data['cash'] = getattr(trader, 'cash', 0)
        if 'shares' not in trader_data:
            trader_data['shares'] = getattr(trader, 'shares', 0)
        if 'goal' not in trader_data:
            trader_data['goal'] = getattr(trader, 'goal', 0)
            
        return trader_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting trader info: {str(e)}"
        )

@app.get("/trader_info/{trader_id}")
async def get_trader_info(trader_id: str):
    # Extract username from trader_id
    if not trader_id.startswith("HUMAN_"):
        raise HTTPException(status_code=404, detail="Invalid trader ID")
    
    username = trader_id[6:]  # Remove "HUMAN_" prefix
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    if session_status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Trader not found")
    
    # If user is in waiting session, return minimal trader info (no session/market IDs)
    if session_status.get("status") == "waiting":
        # Get basic info for session pool user
        historical_markets_count = len(market_handler.user_historical_markets.get(username, set()))
        
        # Create minimal trader data for waiting state
        trader_data = {
            'cash': 100000,  # Default initial cash
            'shares': 300,   # Default initial shares  
            'goal': 0,       # Placeholder goal
            'id': trader_id,
            'all_attributes': {
                'historical_markets_count': historical_markets_count,
                'is_admin': username in ['venvoooo', 'asancetta', 'marjonuzaj', 'fra160756', 'expecon'],
                'params': {},  # Don't expose session status details
                'isWaitingForOthers': True
            }
        }
        
        return {
            "status": "waiting",
            "message": "Trader in session pool, waiting for market to start",
            "data": {
                **trader_data,
                "order_book_metrics": {},
                "trader_specific_metrics": {}
            }
        }
    
    # If market is active, get full trader info using trader ID only
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader not found")

    try:
        trader_data = get_trader_info_with_market_data(trader_manager, trader_id)
        
        # Use internal session/market ID for logging only (don't expose to frontend)
        internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
        log_file_path = os.path.join("logs", f"{internal_session_id}_trading.log")

        try:
            # Check if log file exists before processing
            if os.path.exists(log_file_path):
                print(f"[DEBUG] Processing log file: {log_file_path}")
                print(f"[DEBUG] Looking for trader_id: {trader_id}")
                
                order_book_metrics = order_book_contruction(log_file_path)
                print(f"[DEBUG] Order book metrics keys: {list(order_book_metrics.keys())}")
                
                # Try both with and without quotes for trader ID lookup
                quoted_trader_id = f"'{trader_id}'"
                print(f"[DEBUG] Looking for quoted_trader_id: {quoted_trader_id}")
                print(f"[DEBUG] Also looking for unquoted trader_id: {trader_id}")
                
                # First try with quotes (old format), then without quotes (new format)
                trader_specific_metrics = order_book_metrics.get(quoted_trader_id, {})
                if not trader_specific_metrics:
                    trader_specific_metrics = order_book_metrics.get(trader_id, {})
                print(f"[DEBUG] Found trader_specific_metrics: {bool(trader_specific_metrics)}")
                if trader_specific_metrics:
                    print(f"[DEBUG] Trader metrics keys: {list(trader_specific_metrics.keys())}")
                
                # Exclude both quoted and unquoted trader IDs from general metrics
                trader_keys_to_exclude = {quoted_trader_id, trader_id}
                general_metrics = {k: v for k, v in order_book_metrics.items() if k not in trader_keys_to_exclude}
                print(f"[DEBUG] General metrics keys: {list(general_metrics.keys())}")

                if trader_specific_metrics:
                    trader_goal = trader_data.get('goal', 0)  # Get trader goal from trader data
                    print(f"[DEBUG] Trader goal: {trader_goal}")
                    trader_specific_metrics = calculate_trader_specific_metrics(
                        trader_specific_metrics, 
                        general_metrics, 
                        trader_goal
                    )
                    print(f"[DEBUG] Calculated trader_specific_metrics: {trader_specific_metrics}")
                else:
                    print(f"[DEBUG] No trader-specific metrics found")
                    trader_specific_metrics = {}
            else:
                print(f"Log file not found: {log_file_path}")
                order_book_metrics = {}
                trader_specific_metrics = {}

        except Exception as e:
            print(f"Error processing metrics for trader {trader_id}: {str(e)}")
            print(f"Log file path: {log_file_path}")
            order_book_metrics = {}
            trader_specific_metrics = {}

        # Add flag to indicate not waiting
        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}
        trader_data['all_attributes']['isWaitingForOthers'] = False

        return {
            "status": "success",
            "message": "Trader found",
            "data": {
                **trader_data,
                "order_book_metrics": order_book_metrics,
                "trader_specific_metrics": trader_specific_metrics
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trader info: {str(e)}")

@app.get("/trader/{trader_id}/market")
async def get_trader_market(trader_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    gmail_username = current_user.get('gmail_username', '')
    print(f"Trader/market endpoint called for trader_id: {trader_id}, user: {gmail_username}, is_prolific: {is_prolific}")
    
    # Verify that the current user has access to this trader_id
    # For Prolific users, we need to ensure they can only access their own trader
    if is_prolific and f"HUMAN_{gmail_username}" != trader_id:
        print(f"Prolific user {gmail_username} attempted to access trader {trader_id}")
        raise HTTPException(status_code=403, detail="You can only access your own trader data")
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    if session_status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Please login first to join a trading session")
    
    # If user is in waiting session, return minimal session info (no session/market IDs)
    if session_status.get("status") == "waiting":
        response_data = {
            "status": "waiting",
            "data": {
                "traders": [trader_id],  # Just this trader for now
                "human_traders": [{"id": trader_id}],  # Minimal human trader data
                "game_params": {"predefined_goals": [0], "num_human_traders": 1},  # Placeholder
                "isWaitingForOthers": True
            },
        }
        return response_data
    
    # If market is active, get the trader manager using trader ID only
    trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
    if not trader_manager:
        # This shouldn't happen if session status is active
        print(f"No trader manager found for {trader_id}")
        raise HTTPException(status_code=404, detail="No market found for this trader")

    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]
    params_dict = trader_manager.params.model_dump()
    
    # Add expected traders count based on predefined goals
    params_dict['num_human_traders'] = len(params_dict['predefined_goals'])
    
    # Ensure the human trader has a record even if they don't trade
    # This is important for Prolific users who may not actively trade
    if trader_id.startswith("HUMAN_"):
        for human_trader in trader_manager.human_traders:
            if human_trader.id == trader_id and hasattr(human_trader, 'handle_TRADING_STARTED'):
                # This will ensure the trader has a record in the system
                print(f"Ensuring record for human trader: {trader_id} in market endpoint")

    response_data = {
        "status": "success",
        "data": {
            "traders": list(trader_manager.traders.keys()),
            "human_traders": human_traders_data,
            "game_params": params_dict,
            "isWaitingForOthers": False
        },
    }
    
    return response_data



async def send_to_frontend(websocket: WebSocket, trader_manager):
    while True:
        trading_market = trader_manager.trading_market
        time_update = {
            "type": "time_update",
            "data": {
                "current_time": trading_market.current_time.isoformat(),
                "is_trading_started": trading_market.trading_started,
                "remaining_time": max(0, (
                    trading_market.start_time
                    + timedelta(minutes=trading_market.duration)
                    - trading_market.current_time
                ).total_seconds())
                if trading_market.trading_started
                else None,
                "current_human_traders": len(trader_manager.human_traders),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
            },
        }
        try:
            sanitized_update = sanitize_websocket_message(time_update)
            await websocket.send_json(sanitized_update)
        except Exception as e:
            print(f"Error sending time update: {e}")
        await asyncio.sleep(1)

async def receive_from_frontend(websocket: WebSocket, trader):
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            parsed_message = json.loads(message)
            
            if parsed_message.get('type') == 'order':
                async with trader_locks[trader.id]:
                    await trader.on_message_from_client(message)
            else:
                await trader.on_message_from_client(message)
                
        except (asyncio.TimeoutError, WebSocketDisconnect, json.JSONDecodeError):
            continue
        except Exception:
            return

@app.get("/market_metrics")
async def get_market_metrics(trader_id: str, market_id: str, current_user: dict = Depends(get_current_user)):
    if trader_id != f"HUMAN_{current_user['gmail_username']}":
        raise HTTPException(status_code=403, detail="Unauthorized access to trader data")
    
    log_file_path = f"logs/{market_id}_trading.log"
    
    try:
        processed_data = process_log_file(log_file_path)
        output = io.StringIO()
        write_to_csv(processed_data, output)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=market_{market_id}_trader_{trader_id}_metrics.csv"}
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error processing market metrics")

@app.websocket("/trader/{trader_id}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_id: str):
    await websocket.accept()
    internal_session_id = None
    gmail_username = None
    
    try:
        token = await websocket.receive_text()
        
        # Check if this is a Prolific token
        is_prolific = False
        if token.startswith('prolific_') or token == 'no-auth':
            # Extract username from trader_id for Prolific users
            # Format is typically HUMAN_123456abcdef
            if trader_id.startswith('HUMAN_'):
                gmail_username = trader_id[6:]  # Remove 'HUMAN_' prefix
                is_prolific = True
                print(f"Authenticated Prolific user via WebSocket: {gmail_username}")
        else:
            # Regular Firebase authentication
            try:
                decoded_token = custom_verify_id_token(token)
                email = decoded_token['email']
                gmail_username = extract_gmail_username(email)
            except Exception as e:
                print(f"WebSocket token verification failed: {str(e)}")
                await websocket.close(code=1008, reason="Authentication failed")
                return
        
        if not gmail_username:
            await websocket.close(code=1008, reason="Invalid authentication")
            return
        
        # Check session status using trader ID (simplified approach)
        session_status = market_handler.get_session_status_by_trader_id(trader_id)
        
        if session_status.get("status") == "not_found":
            print(f"Trader {trader_id} not in any session")
            await websocket.close(code=1008, reason="Not in any session")
            return
        
        # If user is in waiting session, handle gracefully
        if session_status.get("status") == "waiting":
            # Send waiting status and close - frontend should show waiting screen
            waiting_message = {
                "type": "session_waiting",
                "data": {
                    "status": "waiting",
                    "message": "Waiting for other traders to join",
                    "isWaitingForOthers": True
                }
            }
            sanitized_waiting = sanitize_websocket_message(waiting_message)
            await websocket.send_json(sanitized_waiting)
            await websocket.close(code=1000, reason="Session waiting")
            return
        
        # If market is active, get the trader manager using trader ID only
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if not trader_manager:
            print(f"No trader manager found for {trader_id} in active market")
            await websocket.close(code=1008, reason="No trader manager found")
            return
            
        # Get internal session/market ID for logging only (don't expose to frontend)
        internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            print(f"No trader found for {trader_id}")
            await websocket.close(code=1008, reason="Trader not found")
            return
        
        market_handler.add_user_to_market(gmail_username, internal_session_id)
        
        initial_count = {
            "type": "trader_count_update",
            "data": {
                "current_human_traders": len(market_handler.active_users.get(internal_session_id, set())),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
                "market_id": internal_session_id
            }
        }
        sanitized_count = sanitize_websocket_message(initial_count)
        await websocket.send_json(sanitized_count)
        
        await trader.connect_to_socket(websocket)
        
        send_task = asyncio.create_task(send_to_frontend(websocket, trader_manager))
        receive_task = asyncio.create_task(receive_from_frontend(websocket, trader))
        
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
            
    except WebSocketDisconnect:
        # Record market if it was active when disconnected
        if internal_session_id and gmail_username and trader_manager and trader_manager.trading_market.trading_started:
            if gmail_username not in market_handler.user_historical_markets:
                market_handler.user_historical_markets[gmail_username] = set()
            market_handler.user_historical_markets[gmail_username].add(internal_session_id)
    except Exception:
        pass
    finally:
        if internal_session_id and gmail_username:
            market_handler.remove_user_from_market(gmail_username, internal_session_id)
            await broadcast_trader_count(internal_session_id)
        try:
            await websocket.close()
        except RuntimeError:
            # Ignore "websocket.close" after response completed error
            pass

current_dir = Path(__file__).resolve().parent
ROOT_DIR = current_dir.parent / "logs"

@app.get("/files")
async def list_files(
    path: str = Query("", description="Relative path to browse")
):
    try:
        full_path = (ROOT_DIR / path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        if full_path.is_file():
            return {"type": "file", "name": full_path.name}
        
        files = []
        directories = []
        
        for item in full_path.iterdir():
            # Get last modified time
            mod_time = datetime.fromtimestamp(item.stat().st_mtime)
            
            if item.is_file():
                files.append({
                    "type": "file", 
                    "name": item.name,
                    "modified": mod_time
                })
            elif item.is_dir():
                directories.append({
                    "type": "directory", 
                    "name": item.name,
                    "modified": mod_time
                })
        
        # Sort files and directories by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        directories.sort(key=lambda x: x["modified"], reverse=True)
        
        # Remove the modification time from the response
        files = [{"type": f["type"], "name": f["name"]} for f in files]
        directories = [{"type": d["type"], "name": d["name"]} for d in directories]
        
        return {
            "current_path": str(full_path.relative_to(ROOT_DIR)),
            "parent_path": str(full_path.parent.relative_to(ROOT_DIR)) if full_path != ROOT_DIR else None,
            "directories": directories,
            "files": files
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    try:
        full_path = (ROOT_DIR / file_path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(full_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
# lets start trading!
@app.post("/trading/start")
async def start_trading_market(background_tasks: BackgroundTasks, request: Request):
    # Special handling for Prolific users
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        # Use the new authenticate_prolific_user function instead of validate_prolific_user directly
        try:
            prolific_user = await authenticate_prolific_user(request)
            if prolific_user:
                current_user = prolific_user
                print(f"Authenticated Prolific user via params in /trading/start: {prolific_user['gmail_username']}")
            else:
                # Fall back to regular authentication if prolific authentication fails
                current_user = await get_current_user(request)
        except HTTPException as e:
            print(f"Prolific authentication failed: {str(e)}")
            # Fall back to regular authentication
            current_user = await get_current_user(request)
    else:
        # Regular authentication for non-Prolific users
        current_user = await get_current_user(request)
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    print(f"Trading/start called for user: {gmail_username}, trader_id: {trader_id}, is_prolific: {is_prolific}")
    
    # Check session status using trader ID (simplified approach)
    session_status = market_handler.get_session_status_by_trader_id(trader_id)
    
    if session_status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="No session found for user")
    
    # Mark trader ready and start trading if possible using trader ID only
    all_ready = await market_handler.mark_trader_ready_by_trader_id(trader_id)
    
    if all_ready:
        status_message = "Trading started successfully!"
        
        # Get the trader manager to start trading session
        trader_manager = market_handler.get_trader_manager_by_trader_id(trader_id)
        if trader_manager:
            # Get internal session/market ID for background tasks only (don't expose to frontend)
            internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
            
            # Actually launch the trading session - this was missing!
            print(f"[DEBUG] Launching trader manager for session {internal_session_id}")
            background_tasks.add_task(trader_manager.launch)
            background_tasks.add_task(broadcast_trader_count, internal_session_id)
    else:
        status_message = "Marked as ready. Waiting for other traders to be ready."
    
    # Get internal session/market ID for ready traders info only (don't expose to frontend)
    internal_session_id = market_handler.trader_to_market_lookup.get(trader_id)
    ready_traders = list(market_handler.market_ready_traders.get(internal_session_id, set()))
    
    return {
        "status": "success",
        "ready_traders": ready_traders,
        "all_ready": all_ready,
        "message": status_message
    }

# Market monitoring endpoint
@app.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List only pending and active market sessions for monitoring"""
    # Clean up any finished markets first
    await market_handler.cleanup_finished_markets()
    
    # Use the elegant new session listing
    return market_handler.list_all_sessions()

@app.post("/sessions/{market_id}/force-start")
async def force_start_session(
    market_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Force start a trading session even if it's not full"""
    if market_id not in market_handler.trader_managers:
        raise HTTPException(status_code=404, detail="Market not found")
        
    manager = market_handler.trader_managers[market_id]
    market = manager.trading_market
    
    if market.trading_started:
        raise HTTPException(status_code=400, detail="Market session already started")
        
    if not market_handler.active_users.get(market_id):
        raise HTTPException(status_code=400, detail="Cannot start empty session")
    
    # Register all active users first
    active_users = market_handler.active_users.get(market_id, set())
    for username in active_users:
        trader_id = f"HUMAN_{username}"
        await manager.trading_market.handle_register_me({
            "trader_id": trader_id,
            "trader_type": "human",
            "gmail_username": username
        })
        # Mark each human trader as ready
        await market_handler.mark_trader_ready(trader_id, market_id)
    
    # Temporarily store the original predefined_goals
    original_goals = manager.params.predefined_goals
    
    # Modify predefined_goals to match current number of users
    manager.params.predefined_goals = [100] * len(active_users)
    
    try:
        # Launch using the normal initialization process
        await manager.launch()
    finally:
        # Restore original predefined_goals
        manager.params.predefined_goals = original_goals
    
    return {"status": "success", "message": "Market session started successfully"}





# keep our user list fresh
async def periodic_update_registered_users():
    while True:
        try:
            form_id = TradingParameters().google_form_id
            get_registered_users(force_update=True, form_id=form_id)
        except Exception:
            pass
        finally:
            await asyncio.sleep(300)  # 5 min sleep

# time offset calc loop
async def periodic_time_offset_calculation():
    while True:
        await asyncio.sleep(3600)  # 1 hour sleep

# startup tasks
@app.on_event("startup")
async def startup_event():
    # Log default parameters at startup
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()
    logger.log_parameter_state(
        current_state=persistent_settings,
        source='system_startup'
    )
    
    # Start background tasks
    asyncio.create_task(periodic_update_registered_users())
    asyncio.create_task(periodic_time_offset_calculation())

# zip up all the files for download
@app.get("/files/download/all")
async def download_all_files():
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file in ROOT_DIR.glob('*'):
                if file.is_file():
                    zip_file.write(file, file.name)
        
        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=all_log_files.zip"}
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# quick market check
def is_market_valid(market_id: str) -> bool:
    """Check if market is active"""
    if market_id not in trader_managers:
        return False
    
    trader_manager = trader_managers[market_id]
    return trader_manager.trading_market.active

# nuke everything from orbit
@app.post("/admin/reset_state")
async def reset_state(current_user: dict = Depends(get_current_admin_user)):
    """Reset all application state except settings"""
    try:
        global persistent_settings, accumulated_rewards
        current_settings = persistent_settings.copy()
        await market_handler.reset_state()
        persistent_settings = current_settings
        accumulated_rewards = {}  # Reset accumulated rewards
        
        # Preserve historical markets by not clearing market_handler.user_historical_markets
        return {
            "status": "success", 
            "message": "Application state reset successfully"
        }
        
    except Exception:
        raise HTTPException(
            status_code=500, 
            detail="Error resetting application state"
        )
        
# headcount!
async def broadcast_trader_count(market_id: str):
    """Broadcast current trader count to all traders"""
    trader_manager = market_handler.trader_managers.get(market_id)
    if not trader_manager:
        return
        
    current_traders = len(market_handler.active_users[market_id])
    expected_traders = len(trader_manager.params.predefined_goals)
    
    count_message = {
        "type": "trader_count_update",
        "data": {
            "current_human_traders": current_traders,
            "expected_human_traders": expected_traders,
            "market_id": market_id
        }
    }
    
    # spread the word
    for trader in trader_manager.human_traders:
        if hasattr(trader, 'websocket') and trader.websocket:
            try:
                sanitized_count_message = sanitize_websocket_message(count_message)
                await trader.websocket.send_json(sanitized_count_message)
            except Exception:
                pass

@app.get("/admin/persistent_settings")
async def get_persistent_settings(current_user: dict = Depends(get_current_admin_user)):
    """Get current persistent settings"""
    return {
        "status": "success",
        "data": persistent_settings
    }

# Prolific settings model
class ProlificSettings(BaseModel):
    settings: Dict[str, str]

# Questionnaire response model
class QuestionnaireResponse(BaseModel):
    trader_id: str
    responses: List[str]

# Consent form data model
class ConsentData(BaseModel):
    trader_id: str = ''  # Make trader_id optional
    user_id: str = ''
    user_type: str = ''  # 'google' or 'prolific'
    prolific_id: str = ''
    consent_given: bool = True
    consent_timestamp: str = ''

# Debug endpoint for consent
@app.post("/consent/debug")
async def debug_consent(data: dict):
    print("\n\n==== CONSENT DEBUG CALLED =====")
    print(f"Received raw data: {data}")
    
    try:
        # Just echo back the data
        return {"status": "success", "received": data}
    except Exception as e:
        print(f"ERROR in debug endpoint: {str(e)}")
        return {"status": "error", "message": str(e)}

# Get Prolific settings from .env file and in-memory storage
@app.get("/admin/prolific-settings")
async def get_prolific_settings(current_user: dict = Depends(get_current_admin_user)):
    # Import the in-memory credentials storage
    from api.prolific_auth import IN_MEMORY_CREDENTIALS
    try:
        env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / ".env"
        
        if not env_path.exists():
            return {
                "status": "error",
                "message": ".env file not found"
            }
        
        # Read the .env file
        env_content = env_path.read_text()
        
        # Extract Prolific settings
        prolific_settings = {}
        
        # First check for credentials in memory
        if IN_MEMORY_CREDENTIALS:
            # Convert in-memory credentials to string format
            creds_str = " ".join([f"{username},{password}" for username, password in IN_MEMORY_CREDENTIALS.items()])
            prolific_settings["PROLIFIC_CREDENTIALS"] = creds_str
            print(f"Returning {len(IN_MEMORY_CREDENTIALS)} credential pairs from memory")
        
        # Extract other settings from .env file
        for line in env_content.splitlines():
            if line.startswith("PROLIFIC_STUDY_ID="):
                prolific_settings["PROLIFIC_STUDY_ID"] = line.split("=", 1)[1]
            elif line.startswith("PROLIFIC_REDIRECT_URL="):
                prolific_settings["PROLIFIC_REDIRECT_URL"] = line.split("=", 1)[1]
            elif line.startswith("PROLIFIC_CREDENTIALS=") and "PROLIFIC_CREDENTIALS" not in prolific_settings:
                # Only use .env credentials if no in-memory credentials exist
                prolific_settings["PROLIFIC_CREDENTIALS"] = line.split("=", 1)[1]
        
        return {
            "status": "success",
            "data": prolific_settings
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Save questionnaire responses
@app.post("/save_questionnaire_response")
async def save_questionnaire_response(response: QuestionnaireResponse):
    try:
        # Create logs directory if it doesn't exist
        questionnaire_dir = ROOT_DIR / "questionnaire"
        questionnaire_dir.mkdir(exist_ok=True)
        
        # Create or append to CSV file
        csv_path = questionnaire_dir / "questionnaire_responses.csv"
        
        # Check if file exists to determine if we need to write headers
        file_exists = csv_path.exists()
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare data row
        row = [timestamp, response.trader_id] + response.responses
        
        # Open file in append mode
        with open(csv_path, 'a', newline='') as f:
            # If file doesn't exist, write headers
            if not file_exists:
                headers = ["timestamp", "trader_id", "question1", "question2", "question3", "question4"]
                f.write(','.join(headers) + '\n')
            
            # Write data row
            f.write(','.join([str(item) for item in row]) + '\n')
        
        return {"status": "success", "message": "Questionnaire response saved successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save questionnaire response: {str(e)}"}

# Download questionnaire responses
@app.get("/admin/download_questionnaire_responses")
async def download_questionnaire_responses(current_user: dict = Depends(get_current_admin_user)):
    try:
        questionnaire_dir = ROOT_DIR / "questionnaire"
        csv_path = questionnaire_dir / "questionnaire_responses.csv"
        
        if not csv_path.exists():
            return Response(
                content="No questionnaire responses found",
                media_type="text/plain"
            )
        
        return FileResponse(
            path=csv_path,
            filename="questionnaire_responses.csv",
            media_type="text/csv"
        )
    except Exception as e:
        return Response(
            content=f"Error downloading questionnaire responses: {str(e)}",
            media_type="text/plain",
            status_code=500
        )

# Save consent form data
@app.post("/consent/save")
async def save_consent_data(consent: ConsentData):
    consent_dir = Path("logs/consent")
    consent_dir.mkdir(parents=True, exist_ok=True)
    consent_file = consent_dir / "consent_data.csv"
    file_exists = consent_file.exists()
    timestamp = datetime.now().isoformat()
    user_id = consent.user_id or consent.prolific_id
    user_type = consent.user_type or ("prolific" if consent.prolific_id else None)
    with open(consent_file, mode='a', newline='') as file:
        fieldnames = ['trader_id', 'user_id', 'user_type', 'consent_given', 'consent_timestamp']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        trader_id = consent.trader_id or user_id
        row_data = {
            'trader_id': trader_id,
            'user_id': user_id,
            'user_type': user_type,
            'consent_given': str(consent.consent_given),
            'consent_timestamp': timestamp
        }
        writer.writerow(row_data)
    return {"status": "success", "message": "Consent data saved successfully", "timestamp": timestamp}


# Download consent data
@app.get("/admin/download-consent-data")
async def download_consent_data(current_user: dict = Depends(get_current_admin_user)):
    consent_dir = ROOT_DIR.parent / "logs/consent"
    consent_file = consent_dir / "consent_data.csv"
    if not consent_file.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "Consent data file not found"})
    return FileResponse(path=consent_file, filename="consent_data.csv", media_type="text/csv")

# Update Prolific settings in .env file
@app.post("/admin/prolific-settings")
async def update_prolific_settings(settings: ProlificSettings, current_user: dict = Depends(get_current_admin_user)):
    # Import the in-memory credentials storage
    from api.prolific_auth import IN_MEMORY_CREDENTIALS
    try:
        # Process and store credentials in memory if provided
        if "PROLIFIC_CREDENTIALS" in settings.settings:
            # Clear existing credentials
            IN_MEMORY_CREDENTIALS.clear()
            
            # Parse the credentials string
            creds_str = settings.settings["PROLIFIC_CREDENTIALS"]
            
            # Process each credential pair
            for cred_pair in creds_str.strip().split():
                parts = cred_pair.strip().split(",")
                if len(parts) == 2:
                    username, password = parts
                    IN_MEMORY_CREDENTIALS[username.strip()] = password.strip()
            
            print(f"Stored {len(IN_MEMORY_CREDENTIALS)} credential pairs in memory")
        
        env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / ".env"
        
        if not env_path.exists():
            return {
                "status": "error",
                "message": ".env file not found"
            }
        
        # Read the .env file
        env_content = env_path.read_text()
        
        # Update Prolific settings
        new_env_content = []
        prolific_credentials_updated = False
        prolific_study_id_updated = False
        prolific_redirect_url_updated = False
        
        for line in env_content.splitlines():
            # Skip updating PROLIFIC_CREDENTIALS in the .env file
            if line.startswith("PROLIFIC_CREDENTIALS="):
                # Don't include this line in the new content
                # We'll store credentials in memory instead
                prolific_credentials_updated = True
            elif line.startswith("PROLIFIC_STUDY_ID=") and "PROLIFIC_STUDY_ID" in settings.settings:
                new_env_content.append(f"PROLIFIC_STUDY_ID={settings.settings['PROLIFIC_STUDY_ID']}")
                prolific_study_id_updated = True
            elif line.startswith("PROLIFIC_REDIRECT_URL=") and "PROLIFIC_REDIRECT_URL" in settings.settings:
                new_env_content.append(f"PROLIFIC_REDIRECT_URL={settings.settings['PROLIFIC_REDIRECT_URL']}")
                prolific_redirect_url_updated = True
            else:
                new_env_content.append(line)
        
        # Add settings that weren't updated (they didn't exist in the file)
        # Skip adding PROLIFIC_CREDENTIALS to the .env file
        # We'll store credentials in memory instead
        
        if not prolific_study_id_updated and "PROLIFIC_STUDY_ID" in settings.settings:
            new_env_content.append(f"PROLIFIC_STUDY_ID={settings.settings['PROLIFIC_STUDY_ID']}")
        
        if not prolific_redirect_url_updated and "PROLIFIC_REDIRECT_URL" in settings.settings:
            new_env_content.append(f"PROLIFIC_REDIRECT_URL={settings.settings['PROLIFIC_REDIRECT_URL']}")
        
        # Write the updated content back to the .env file
        env_path.write_text("\n".join(new_env_content))
        
        return {
            "status": "success",
            "message": "Prolific settings updated successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
