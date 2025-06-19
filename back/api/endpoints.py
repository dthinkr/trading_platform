import asyncio
import io
import time
from datetime import timedelta, datetime

# main imports
from fastapi import (
    FastAPI, WebSocket, HTTPException, WebSocketDisconnect, 
    BackgroundTasks, Depends, Request, Response
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic

# our stuff - new beautiful architecture
from .market_pipeline import MarketPipeline
from core.trader_manager import TraderManager
from core.data_models import TraderType, TradingParameters, UserRegistration, TraderRole
from .auth import get_current_user, get_current_admin_user, extract_gmail_username, is_user_registered, is_user_admin, custom_verify_id_token
from .prolific_auth import extract_prolific_params, validate_prolific_user, authenticate_prolific_user
from .calculate_metrics import process_log_file, write_to_csv
from .logfiles_analysis import order_book_contruction, calculate_trader_specific_metrics
from firebase_admin import auth

# python stuff we need
import json
from pydantic import BaseModel, ValidationError
import os
import csv
from fastapi import HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, Any, List
from .google_sheet_auth import update_form_id, get_registered_users
import zipfile
from utils import setup_custom_logger
from datetime import datetime
from .random_picker import pick_random_element_new

# init fastapi
app = FastAPI()
security = HTTPBasic()

# Global variables - MINIMAL STATE
from core.data_models import TradingParameters

# Global instances - beautiful and clean
market_pipeline = MarketPipeline()
accumulated_rewards = {}  # Store accumulated rewards per user

# Initialize with default values from TradingParameters
default_params = TradingParameters()
persistent_settings = default_params.model_dump()

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

# Models
class PersistentSettings(BaseModel):
    settings: dict

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/user/login")
async def user_login(request: Request):
    """Simple login - just authenticate user, no market assignment"""
    # Check for Prolific parameters first
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        try:
            prolific_user = await authenticate_prolific_user(request)
            if prolific_user:
                gmail_username = prolific_user['gmail_username']
                prolific_token = prolific_user.get('prolific_token', '')
                
                print(f"Authenticated Prolific user: {gmail_username}")
                
                return {
                    "status": "success",
                    "message": "Prolific login successful",
                    "data": {
                        "username": gmail_username,
                        "is_admin": False,
                        "is_prolific": True,
                        "prolific_token": prolific_token
                    }
                }
            else:
                raise HTTPException(status_code=401, detail="Invalid Prolific credentials")
        except HTTPException as e:
            raise e
    
    # Regular Firebase authentication
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    token = auth_header.split('Bearer ')[1]
    decoded_token = custom_verify_id_token(token)
    email = decoded_token['email']
    gmail_username = extract_gmail_username(email)
    
    # Check registration for non-admin users
    if not is_user_admin(email):
        form_id = TradingParameters().google_form_id
        if not is_user_registered(email, form_id):
            raise HTTPException(status_code=403, detail="User not registered in the study")
    
    return {
        "status": "success",
        "message": "Login successful",
        "data": {
            "username": email,
            "is_admin": is_user_admin(email),
            "is_prolific": False
        }
    }

@app.post("/admin/login")
async def admin_login(request: Request):
    """Admin login"""
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

# ============================================================================
# ONBOARDING ENDPOINTS
# ============================================================================

@app.post("/user/complete-onboarding")
async def complete_onboarding(request: Request, current_user: dict = Depends(get_current_user)):
    """Mark user as having completed onboarding process"""
    try:
        gmail_username = current_user['gmail_username']
        is_prolific = current_user.get('is_prolific', False)
        
        print(f"User {gmail_username} completed onboarding (prolific: {is_prolific})")
        
        return {
            "status": "success",
            "message": "Onboarding completed successfully",
            "data": {
                "username": gmail_username,
                "onboarding_complete": True,
                "is_prolific": is_prolific
            }
        }
        
    except Exception as e:
        print(f"Error completing onboarding for user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete onboarding: {str(e)}")

# ============================================================================
# WAITING ROOM ENDPOINTS
# ============================================================================

@app.post("/user/join-waiting-room")
async def join_waiting_room_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Join waiting room using beautiful constraint-based matching"""
    try:
        gmail_username = current_user['gmail_username']
        is_prolific = current_user.get('is_prolific', False)
        
        # Get trading parameters
        params = TradingParameters(**(persistent_settings or {}))
        
        print(f"🎯 User {gmail_username} joining constraint-based matching system")
        
        # Use beautiful market pipeline
        market_ready, result_data = await market_pipeline.join_queue(gmail_username, is_prolific, params)
        
        if market_ready:
            # Find this user's assignment
            user_data = next((u for u in result_data["users"] if u["username"] == gmail_username), None)
            
            if user_data:
                market_id = result_data["market_id"]
                return {
                    "status": "success",
                    "message": f"✨ Market ready! Trading in {market_id}",
                    "data": {
                        "session_ready": True,  # Keep for frontend compatibility
                        "market_id": market_id,
                        "trader_id": user_data["trader_id"],
                        "role": user_data["role"],
                        "goal": user_data["goal"]
                    }
                }
            else:
                raise HTTPException(status_code=500, detail="User not found in market data")
        else:
            # Still waiting - return detailed pool status
            return {
                "status": "success",
                "message": f"⏳ Waiting for more players...",
                "data": result_data
            }
            
    except Exception as e:
        print(f"Error joining waiting room: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to join waiting room: {str(e)}")

@app.get("/user/waiting-room-status")
async def get_waiting_room_status_endpoint(current_user: dict = Depends(get_current_user)):
    """Get current waiting room status for user"""
    try:
        gmail_username = current_user['gmail_username']
        
        # Check if user has a market assignment
        market_id = market_pipeline.get_market_for_user(gmail_username)
        if market_id:
            # User is already assigned to a market
            return {
                "status": "success",
                "data": {
                    "in_waiting_room": False,
                    "session_ready": True,
                    "market_id": market_id
                }
            }
        
        # Check waiting room status
        status = market_pipeline.get_user_status(gmail_username)
        return {
            "status": "success",
            "data": status
        }
        
    except Exception as e:
        print(f"Error getting waiting room status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get waiting room status")

@app.get("/trader_info/{trader_id}")
async def get_trader_info(trader_id: str, current_user: dict = Depends(get_current_user)):
    """Get trader information"""
    try:
        gmail_username = current_user['gmail_username']
        is_prolific = current_user.get('is_prolific', False)
        
        print(f"=== DEBUG: Getting trader info for {trader_id} ===")
        print(f"User: {gmail_username}, Prolific: {is_prolific}")
        
        # Debug: Show available traders
        available_traders = list(market_pipeline.trader_to_market.keys())
        print(f"Available traders in market_pipeline: {available_traders}")
        
        # Get trader manager for this trader
        trader_manager = market_pipeline.get_trader_manager(trader_id)
        print(f"Trader manager found: {trader_manager is not None}")
        
        if not trader_manager:
            print(f"ERROR: No trader manager found for {trader_id}")
            print(f"Market pipeline state: {len(market_pipeline.markets)} markets, {len(market_pipeline.trader_to_market)} trader mappings")
            raise HTTPException(status_code=404, detail="Trader not found or not assigned to market yet")
        
        print(f"Trader manager has {len(trader_manager.traders)} traders")
        print(f"Trader IDs in manager: {list(trader_manager.traders.keys())}")
        
        trader = trader_manager.get_trader(trader_id)
        print(f"Trader found in manager: {trader is not None}")
        
        if not trader:
            print(f"ERROR: Trader {trader_id} not found in manager")
            raise HTTPException(status_code=404, detail="Trader not found in market")
        
        print(f"Trader type: {type(trader)}")
        print(f"Trader attributes: {dir(trader)}")
        
        # Safe attribute access with debugging
        role = "unknown"
        if hasattr(trader, 'role'):
            role = trader.role.value if hasattr(trader.role, 'value') else str(trader.role)
            print(f"Trader role: {role}")
        else:
            print("WARNING: Trader has no 'role' attribute")
            
        goal = getattr(trader, 'goal', 0)
        print(f"Trader goal: {goal}")
        
        result = {
            "trader_id": trader_id,
            "role": role,
            "goal": goal,
            "current_value": getattr(trader, 'current_value', 0),
            "current_holdings": getattr(trader, 'current_holdings', 0),
            "cash": getattr(trader, 'cash', 0),
            "market_id": trader_manager.trading_market.id
        }
        
        print(f"Returning result: {result}")
        return result
        
    except Exception as e:
        print(f"=== ERROR in get_trader_info ===")
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get trader info: {str(e)}")

# ============================================================================
# TRADING ENDPOINTS
# ============================================================================

@app.post("/trading/initiate")
async def create_trading_market(background_tasks: BackgroundTasks, request: Request, current_user: dict = Depends(get_current_user)):
    """Initialize trading for a user who has been assigned to a market"""
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
    
    trader_manager = market_pipeline.get_trader_manager(trader_id)
    if not trader_manager:
        # For debugging purposes, log all available trader managers
        available_traders = list(market_pipeline.trader_to_market.keys())
        print(f"No trader manager found for {trader_id}. Available traders: {available_traders}")
        raise HTTPException(status_code=404, detail="No active market found for this user")
    
    market_id = market_pipeline.trader_to_market.get(trader_id)
    
    # Update the manager's parameters with our merged params
    trader_manager.params = merged_params
    
    response_data = {
        "status": "success",
        "message": "Trading market info retrieved",
        "data": {
            "trading_market_uuid": market_id,
            "trader_id": trader_id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": [t.id for t in trader_manager.human_traders],
            "num_human_traders": len(merged_params.predefined_goals)
        }
    }
    
    return response_data

@app.post("/trading/start")
async def start_trading_market(background_tasks: BackgroundTasks, request: Request):
    """Start trading for a market"""
    # Handle authentication (Prolific or regular)
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        try:
            prolific_user = await authenticate_prolific_user(request)
            if prolific_user:
                current_user = prolific_user
                print(f"Authenticated Prolific user via params in /trading/start: {prolific_user['gmail_username']}")
            else:
                current_user = await get_current_user(request)
        except HTTPException as e:
            current_user = await get_current_user(request)
    else:
        current_user = await get_current_user(request)
    
    gmail_username = current_user['gmail_username']
    is_prolific = current_user.get('is_prolific', False)
    trader_id = f"HUMAN_{gmail_username}"
    
    print(f"Trading/start called for user: {gmail_username}, trader_id: {trader_id}, is_prolific: {is_prolific}")
    
    try:
        # Get current parameters
        params = TradingParameters(**(persistent_settings or {}))
        
        # Mark trader as ready and start market if all ready
        all_ready = await market_pipeline.mark_trader_ready(trader_id)
        
        if all_ready:
            # Start the market
            success = await market_pipeline.start_market(trader_id, params)
            if success:
                status_message = "Trading started!"
                print(f"Market started successfully for trader {trader_id}")
            else:
                status_message = "Failed to start market"
                print(f"Failed to start market for trader {trader_id}")
        else:
            status_message = "Waiting for other traders to be ready"
        
        return {
            "status": "success",
            "all_ready": all_ready,
            "message": status_message
        }
        
    except Exception as e:
        print(f"Error in start_trading_market: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start trading: {str(e)}")

# ============================================================================
# TRADER INFO ENDPOINTS
# ============================================================================

def get_manager_by_trader(trader_id: str):
    """Get trader manager for trader ID"""
    return market_pipeline.get_trader_manager(trader_id)

@app.get("/trader/{trader_id}")
async def get_trader(trader_id: str, current_user: dict = Depends(get_current_user)):
    trader_manager = get_manager_by_trader(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader = trader_manager.traders.get(trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader_data = trader.get_trader_params_as_dict()
    data = trader_manager.get_params()
    data["goal"] = trader_data["goal"]
    return {"status": "success", "message": "Trader found", "data": data}

@app.get("/trader/{trader_id}/market")
async def get_trader_market(trader_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Get market info for a trader"""
    # Log authentication info for debugging
    is_prolific = current_user.get('is_prolific', False)
    gmail_username = current_user.get('gmail_username', '')
    print(f"Trader/market endpoint called for trader_id: {trader_id}, user: {gmail_username}, is_prolific: {is_prolific}")
    
    # Verify that the current user has access to this trader_id
    if is_prolific and f"HUMAN_{gmail_username}" != trader_id:
        print(f"Prolific user {gmail_username} attempted to access trader {trader_id}")
        raise HTTPException(status_code=403, detail="You can only access your own trader data")
    
    trader_manager = market_pipeline.get_trader_manager(trader_id)
    if not trader_manager:
        available_traders = list(market_pipeline.trader_to_market.keys())
        print(f"No trader manager found for {trader_id}. Available traders: {available_traders}")
        raise HTTPException(status_code=404, detail="No market found for this trader")

    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]
    params_dict = trader_manager.params.model_dump()
    
    # Add expected traders count based on predefined goals
    params_dict['num_human_traders'] = len(params_dict['predefined_goals'])

    response_data = {
        "status": "success",
        "data": {
            "trading_market_uuid": trader_manager.trading_market.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": human_traders_data,
            "game_params": params_dict
        },
    }
    
    return response_data

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/admin/update_persistent_settings")
async def update_persistent_settings(settings: PersistentSettings):
    global persistent_settings
    
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

@app.get("/admin/persistent_settings")
async def get_persistent_settings_admin(current_user: dict = Depends(get_current_admin_user)):
    """Get current persistent settings for admin"""
    return {
        "status": "success",
        "data": persistent_settings
    }

@app.post("/admin/reset_state")
async def reset_state(current_user: dict = Depends(get_current_admin_user)):
    """Reset all application state except settings"""
    try:
        global persistent_settings, accumulated_rewards
        current_settings = persistent_settings.copy()
        
        # Reset market pipeline
        await market_pipeline.reset_all()
        
        # Restore settings and reset rewards
        persistent_settings = current_settings
        accumulated_rewards = {}
        
        return {
            "status": "success", 
            "message": "Application state reset successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error resetting application state")

@app.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List current market pipeline status and active markets"""
    # Get market pipeline debug info
    await market_pipeline.cleanup_finished_markets()
    pipeline_info = market_pipeline.get_debug_info()
    
    return pipeline_info

# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/trader/{trader_id}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_id: str):
    await websocket.accept()
    market_id = None
    gmail_username = None
    
    try:
        token = await websocket.receive_text()
        
        # Check if this is a Prolific token
        is_prolific = False
        if token.startswith('prolific_') or token == 'no-auth':
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
        
        trader_manager = market_pipeline.get_trader_manager(trader_id)
        if not trader_manager:
            print(f"No trader manager found for {trader_id}")
            await websocket.close(code=1008, reason="No trader manager found")
            return
            
        market_id = market_pipeline.trader_to_market.get(trader_id)
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            print(f"No trader found for {trader_id}")
            await websocket.close(code=1008, reason="Trader not found")
            return
        
        market_pipeline.add_active_user(gmail_username, market_id)
        
        initial_count = {
            "type": "trader_count_update",
            "data": {
                "current_human_traders": len(market_pipeline.active_users.get(market_id, set())),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
                "market_id": market_id
            }
        }
        await websocket.send_json(initial_count)
        
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
        # Just log the disconnection
        if market_id and gmail_username:
            print(f"User {gmail_username} disconnected from market {market_id}")
    except Exception:
        pass
    finally:
        if market_id and gmail_username:
            market_pipeline.remove_active_user(gmail_username, market_id)
        try:
            await websocket.close()
        except RuntimeError:
            pass

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def send_to_frontend(websocket: WebSocket, trader_manager):
    while True:
        trading_market = trader_manager.trading_market
        time_update = {
            "type": "time_update",
            "data": {
                "current_time": trading_market.current_time.isoformat(),
                "is_trading_started": trading_market.trading_started,
                "remaining_time": (
                    trading_market.start_time
                    + timedelta(minutes=trading_market.duration)
                    - trading_market.current_time
                ).total_seconds()
                if trading_market.trading_started
                else None,
                "current_human_traders": len(trader_manager.human_traders),
                "expected_human_traders": len(trader_manager.params.predefined_goals),
            },
        }
        await websocket.send_json(time_update)
        await asyncio.sleep(1)

async def receive_from_frontend(websocket: WebSocket, trader):
    """Handle messages from frontend"""
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            parsed_message = json.loads(message)
            
            await trader.on_message_from_client(message)
                
        except (asyncio.TimeoutError, WebSocketDisconnect, json.JSONDecodeError):
            continue
        except Exception:
            return

# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "status": "trading is active",
        "comment": "this is only for accessing trading platform mostly via websockets",
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

# ============================================================================
# STARTUP
# ============================================================================

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
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    """Periodic cleanup of stale sessions"""
    while True:
        try:
            market_pipeline.cleanup_old_users()
            await market_pipeline.cleanup_finished_markets()
        except Exception as e:
            print(f"Error in periodic cleanup: {str(e)}")
        finally:
            await asyncio.sleep(300)  # 5 minutes 