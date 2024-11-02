import asyncio
import io
from datetime import timedelta, datetime
from uuid import UUID, uuid4

# main imports
from fastapi import (
    FastAPI, WebSocket, HTTPException, WebSocketDisconnect, 
    BackgroundTasks, Depends, status, Request
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_400_BAD_REQUEST
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
import polars as pl
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder

# our stuff
from core.trader_manager import TraderManager
from core.data_models import TraderType, TradingParameters, UserRegistration
from .auth import get_current_user, get_current_admin_user, get_firebase_auth, extract_gmail_username, is_user_registered, is_user_admin, update_google_form_id, custom_verify_id_token
from .calculate_metrics import process_log_file, write_to_csv
from .logfiles_analysis import order_book_contruction, is_jsonable, calculate_trader_specific_metrics
from firebase_admin import auth

# python stuff we need
import secrets
import traceback
import json
from pydantic import BaseModel, ValidationError
import os
from fastapi import HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Dict, Any
from .google_sheet_auth import update_form_id, get_registered_users
import zipfile
import shutil
from collections import defaultdict
import time
import jwt
import numpy as np
import random
from utils import setup_custom_logger
import ssl
from asyncio import Lock
from asyncio import sleep

# setup logging
logger = setup_custom_logger(__name__)

# init fastapi
app = FastAPI()
security = HTTPBasic()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# global state stuff
trader_managers = {}
trader_to_session_lookup = {}
trader_manager: TraderManager = None
persistent_settings = {}

# user tracking
active_users = defaultdict(set)  # session -> users
user_sessions = {}  # user -> session
user_historical_sessions = defaultdict(set)  # user -> all sessions ever

# role tracking 
user_roles = {}  # user -> role
session_informed_traders = defaultdict(str)  # session -> informed trader

# session tracking
session_creation_times = {}  # when sessions were made
SESSION_TIMEOUT = 60  # how long til timeout
session_ready_traders = defaultdict(set)  # who's ready to go

# goal tracking
user_goals = {}  # user -> goal
goal_assignments = {}  # session -> used goals

# locks for thread safety
session_assignment_lock = Lock()
state_lock = Lock()
cleanup_lock = Lock()
session_locks = defaultdict(Lock)  # per-session locks
trader_locks = defaultdict(Lock)   # per-trader locks

# test mode stuff
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
TEST_ADMIN_TOKEN = "test_admin_token_for_load_testing"

# helper funcs
def get_historical_sessions_count(username):
    return len(user_historical_sessions[username])

def record_session_for_user(username, session_id):
    user_historical_sessions[username].add(session_id)

class PersistentSettings(BaseModel):
    settings: dict

@app.post("/admin/update_persistent_settings")
async def update_persistent_settings(settings: PersistentSettings):
    global persistent_settings
    persistent_settings = settings.settings
    return {"status": "success", "message": "Persistent settings updated"}

@app.get("/admin/get_persistent_settings")
async def get_persistent_settings():
    return {"status": "success", "data": persistent_settings}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")

@app.post("/user/login")
async def user_login(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    try:
        token = auth_header.split('Bearer ')[1]
        
        # verify token with some clock skew allowed
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        email = decoded_token['email']
        
        form_id = TradingParameters().google_form_id
        if not is_user_registered(email, form_id):
            raise HTTPException(status_code=403, detail="User not registered in the study")
        
        gmail_username = extract_gmail_username(email)
        
        # admin check
        is_admin = is_user_admin(email)
        
        # check session limits unless admin
        if not is_admin:
            historical_sessions_count = get_historical_sessions_count(gmail_username)
            if historical_sessions_count >= persistent_settings.get('max_sessions_per_human', 4):
                raise HTTPException(status_code=403, detail="Maximum number of allowed sessions reached for this user")
        
        session_id, trader_id = await find_or_create_session_and_assign_trader(gmail_username)
        
        # track the user
        active_users[session_id].add(gmail_username)
        user_sessions[gmail_username] = session_id
        
        # remember they did this session
        record_session_for_user(gmail_username, session_id)
        
        return {
            "status": "success",
            "message": "Login successful and trader assigned",
            "data": {
                "username": email,
                "is_admin": is_admin,
                "session_id": session_id,
                "trader_id": trader_id
            }
        }
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/admin/login")
async def admin_login(request: Request):
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authentication method")
    
    try:
        token = auth_header.split('Bearer ')[1]
        
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
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
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admin login failed: {str(e)}")

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
async def create_trading_session(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    global persistent_settings
    
    try:
        print("\n=== Trading Session Initiation ===")
        print(f"Current user: {current_user}")
        print(f"Persistent settings: {persistent_settings}")
        
        try:
            merged_params = TradingParameters(**persistent_settings)
            print(f"Successfully created TradingParameters with: {merged_params.model_dump()}")
        except ValidationError as e:
            print(f"ValidationError creating TradingParameters: {str(e)}")
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            print(f"Unexpected error creating TradingParameters: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
        gmail_username = current_user['gmail_username']
        print(f"Gmail username: {gmail_username}")
        
        trader_id = f"HUMAN_{gmail_username}"
        print(f"Looking for trader_id: {trader_id}")
        
        session_id = trader_to_session_lookup.get(trader_id)
        print(f"Found session_id: {session_id}")
        
        if not session_id:
            print("No active session found for this user")
            raise HTTPException(status_code=404, detail="No active session found for this user")
        
        trader_manager = trader_managers[session_id]
        print(f"Found trader manager for session {session_id}")
        
        trader_manager.params = merged_params
        print("Updated trader manager params")
        
        response_data = {
            "status": "success",
            "message": "Trading session info retrieved",
            "data": {
                "trading_session_uuid": session_id,
                "trader_id": trader_id,
                "traders": list(trader_manager.traders.keys()),
                "human_traders": [t.id for t in trader_manager.human_traders],
            }
        }
        print(f"Prepared response: {response_data}")
        print("=== Trading Session Initiation Complete ===\n")
        
        return response_data
        
    except Exception as e:
        print(f"ERROR in create_trading_session: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving trading session info: {str(e)}"
        )

def get_manager_by_trader(trader_id: str):
    if trader_id not in trader_to_session_lookup.keys():
        return None
    trading_session_id = trader_to_session_lookup[trader_id]
    manager = trader_managers[trading_session_id]
    return manager

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

def get_trader_info_with_session_data(trader_manager: TraderManager, trader_id: str) -> Dict[str, Any]:
    """get all the trader info plus session stuff"""
    try:
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail="Trader not found")
        
        # get basic trader stuff
        trader_data = trader.get_trader_params_as_dict()
        
        # make sure we have a place for extra stuff
        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}
            
        # get username from trader id
        gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None
        
        # how many sessions they've done
        historical_sessions_count = len(user_historical_sessions.get(gmail_username, set()))
        
        # get session settings
        params = trader_manager.params.model_dump() if trader_manager.params else {}
        
        # check if they're special
        admin_users = params.get('admin_users', [])
        is_admin = gmail_username in admin_users if gmail_username else False
        
        # add the extra stuff
        trader_data['all_attributes'].update({
            'historical_sessions_count': historical_sessions_count,
            'is_admin': is_admin,
            'params': params
        })
        
        # make sure we have the basics
        if 'cash' not in trader_data:
            trader_data['cash'] = getattr(trader, 'cash', 0)
        if 'shares' not in trader_data:
            trader_data['shares'] = getattr(trader, 'shares', 0)
        if 'goal' not in trader_data:
            trader_data['goal'] = getattr(trader, 'goal', 0)
            
        return trader_data
        
    except Exception as e:
        print(f"Error in get_trader_info_with_session_data: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting trader info: {str(e)}"
        )

@app.get("/trader_info/{trader_id}")
async def get_trader_info(trader_id: str):
    print(f"Accessing trader info for trader_id: {trader_id}")

    trader_manager = get_manager_by_trader(trader_id)
    if not trader_manager:
        print(f"Trader manager not found for trader_id: {trader_id}")
        raise HTTPException(status_code=404, detail="Trader not found")

    try:
        # get all the trader details
        trader_data = get_trader_info_with_session_data(trader_manager, trader_id)
        
        # find their session
        session_id = trader_to_session_lookup.get(trader_id)
        
        # get their trading history
        log_file_path = os.path.join("logs", f"{session_id}_trading.log")
        
        try:
            order_book_metrics = order_book_contruction(log_file_path)
            
            # just their stuff
            trader_specific_metrics = order_book_metrics.get(f"'{trader_id}'", {})
            
            # everyone else's stuff
            general_metrics = {k: v for k, v in order_book_metrics.items() if k != f"'{trader_id}'"}

            # crunch their numbers
            trader_specific_metrics = calculate_trader_specific_metrics(
                trader_specific_metrics, 
                general_metrics, 
                trader_data.get('goal', 0)
            )

        except Exception as e:
            general_metrics = {"error": "Unable to process log file"}
            trader_specific_metrics = {}

        return {
            "status": "success",
            "message": "Trader found",
            "data": {
                **trader_data,  # all their basic info
                "order_book_metrics": general_metrics,
                "trader_specific_metrics": trader_specific_metrics
            }
        }
        
    except Exception as e:
        print(f"Error getting trader info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting trader info: {str(e)}")

@app.get("/trader/{trader_id}/session")
async def get_trader_session(trader_id: str, current_user: dict = Depends(get_current_user)):
    session_id = trader_to_session_lookup.get(trader_id)
    if not session_id:
        raise HTTPException(status_code=404, detail="No session found for this trader")
    
    trader_manager = trader_managers.get(session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Trader manager not found")

    human_traders_data = [t.get_trader_params_as_dict() for t in trader_manager.human_traders]

    response_data = {
        "status": "success",
        "data": {
            "trading_session_uuid": trader_manager.trading_session.id,
            "traders": list(trader_manager.traders.keys()),
            "human_traders": human_traders_data,
            "game_params": trader_manager.params.model_dump()
        },
    }
    
    return response_data

@app.get("/traders/list")
async def list_traders(current_user: dict = Depends(get_current_admin_user)):
    return {
        "status": "success",
        "message": "List of traders",
        "data": {"traders": list(trader_manager.traders.keys())},
    }


@app.get("/")
async def root():
    return {
        "status": "trading is active",
        "comment": "this is only for accessing trading platform mostly via websockets",
    }

async def check_session_timeout(session_id: str):
    """check if we need to kill an old session"""
    if session_id not in session_creation_times:
        return False
    
    elapsed_time = time.time() - session_creation_times[session_id]
    if elapsed_time > SESSION_TIMEOUT and not trader_managers[session_id].trading_session.trading_started:
        print(f"Session {session_id} timed out after {elapsed_time:.1f} seconds")
        await cleanup_session(session_id, reason="timeout")
        return True
    return False

async def cleanup_session(session_id: str, reason: str = "normal"):
    """clean up everything about a session"""
    async with cleanup_lock:
        try:
            if session_id not in trader_managers:
                return False
                
            trader_manager = trader_managers[session_id]
            
            # remember who was here
            affected_users = active_users.get(session_id, set()).copy()
            
            # clean up the manager
            await trader_manager.cleanup()
            
            # clean up all the tracking
            if session_id in trader_managers:
                del trader_managers[session_id]
            
            if session_id in goal_assignments:
                del goal_assignments[session_id]
                
            if session_id in session_ready_traders:
                del session_ready_traders[session_id]
                
            if session_id in session_creation_times:
                del session_creation_times[session_id]
                
            # clean up user stuff
            for username in affected_users:
                if username in user_sessions:
                    del user_sessions[username]
                    
            if session_id in active_users:
                del active_users[session_id]
            
            # clean up trader lookups
            traders_to_remove = [
                tid for tid, sid in trader_to_session_lookup.items() 
                if sid == session_id
            ]
            for trader_id in traders_to_remove:
                del trader_to_session_lookup[trader_id]
                
            return True
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            return False

# Add these to the global state variables at the top
ROLE_INFORMED = "informed"
ROLE_SPECULATOR = "speculator"
session_informed_roles = {}  # session_id -> username of informed trader

async def find_or_create_session_and_assign_trader(gmail_username):
    async with session_assignment_lock:  # lock while assigning
        try:
            print(f"\n=== Starting session assignment for {gmail_username} ===")
            print(f"Current trader_managers: {list(trader_managers.keys())}")
            print(f"Current user_sessions: {user_sessions}")
            print(f"Current trader_to_session_lookup: {trader_to_session_lookup}")
            
            # First check - if already in session, validate it still exists
            if gmail_username in user_sessions:
                session_id = user_sessions[gmail_username]
                trader_id = f"HUMAN_{gmail_username}"
                
                if session_id in trader_managers:
                    # Session exists and trading hasn't started - can rejoin
                    trader_manager = trader_managers[session_id]
                    if not trader_manager.trading_session.trading_started:
                        print(f"User rejoining session: {session_id}")
                        # Re-add to active users if needed
                        active_users[session_id].add(gmail_username)
                        trader_to_session_lookup[trader_id] = session_id
                        return session_id, trader_id
                    else:
                        print(f"Session {session_id} already started, cleaning up references")
                
                # Session invalid or started - clean up references
                print(f"Cleaning up invalid session reference: {session_id}")
                del user_sessions[gmail_username]
                if trader_id in trader_to_session_lookup:
                    del trader_to_session_lookup[trader_id]

            # Get user's historical role if any
            historical_role = user_roles.get(gmail_username)
            print(f"User's historical role: {historical_role}")

            # Retry logic for finding available session
            max_retries = 5
            retry_delay = 0.5  # 500ms between retries
            total_delay = 0  # track total delay

            for attempt in range(max_retries):
                print(f"\nAttempt {attempt + 1} to find session")
                print(f"Current trader_managers: {list(trader_managers.keys())}")
                
                # Check again if user got assigned while we were waiting
                if gmail_username in user_sessions:
                    session_id = user_sessions[gmail_username]
                    trader_id = f"HUMAN_{gmail_username}"
                    if session_id in trader_managers:
                        print(f"User assigned to session during retry: {session_id}")
                        return session_id, trader_id

                # Look for available session
                available_session = None
                available_session_id = None
                
                for session_id, manager in trader_managers.items():
                    current_traders = len(active_users[session_id])
                    expected_traders = manager.params.num_human_traders
                    print(f"Checking session {session_id}: {current_traders}/{expected_traders} traders")
                    print(f"Trading started: {manager.trading_session.trading_started}")
                    
                    # Check if this session already has an informed trader
                    session_has_informed = session_id in session_informed_roles
                    can_join = True
                    
                    # If user is historically informed, they can only join sessions without informed
                    if historical_role == ROLE_INFORMED and session_has_informed:
                        can_join = False
                        print(f"Session {session_id} already has informed trader")
                    
                    if (current_traders < expected_traders and 
                        not manager.trading_session.trading_started and
                        can_join):
                        available_session = manager
                        available_session_id = session_id
                        print(f"Found available session: {session_id}")
                        break

                if available_session:
                    break
                    
                # If no session found and not last attempt, wait before retry
                if attempt < max_retries - 1:
                    print(f"No session found, attempt {attempt + 1}/{max_retries}, waiting...")
                    await sleep(retry_delay)
                    total_delay += retry_delay

            # If we still don't have a session after retries, create new one
            if not available_session:
                print("\nCreating new session:")
                print(f"No available session found after {max_retries} retries")
                params = TradingParameters(**persistent_settings)
                new_trader_manager = TraderManager(params)
                
                session_id = new_trader_manager.trading_session.id
                trader_managers[session_id] = new_trader_manager
                session_creation_times[session_id] = time.time()
                available_session = new_trader_manager
                available_session_id = session_id
                goal_assignments[session_id] = []
                print(f"Created new session: {session_id}")

            # Assign role and goal
            if historical_role:
                # Keep consistent role
                role = historical_role
            else:
                # New user - if session has no informed trader and we haven't hit max informed,
                # they can be informed
                if available_session_id not in session_informed_roles:
                    role = ROLE_INFORMED
                    session_informed_roles[available_session_id] = gmail_username
                else:
                    role = ROLE_SPECULATOR
                user_roles[gmail_username] = role

            # Set goal based on role
            if role == ROLE_INFORMED:
                # Informed traders get non-zero goals
                goals = [g for g in available_session.params.predefined_goals if g != 0]
                goal = random.choice(goals) if goals else 100  # fallback to 100
            else:
                # Speculators get 0 or small goals
                goal = 0

            print(f"Assigned role {role} with goal {goal} to {gmail_username}")
            
            # Add them to the session
            trader_id = await available_session.add_human_trader(gmail_username, goal=goal)
            trader_to_session_lookup[trader_id] = available_session_id
            active_users[available_session_id].add(gmail_username)
            user_sessions[gmail_username] = available_session_id
            
            print(f"\n=== Final Session State ===")
            print(f"Session ID: {available_session_id}")
            print(f"Trader ID: {trader_id}")
            print(f"Role: {role}")
            print(f"Goal: {goal}")
            print(f"Active users in session: {active_users[available_session_id]}")
            print(f"Session in trader_managers: {available_session_id in trader_managers}")
            print(f"=== Session assignment complete after {total_delay:.1f}s delay ===\n")
            
            return available_session_id, trader_id
            
        except Exception as e:
            print(f"\nERROR in session assignment:")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print(f"Current state:")
            print(f"trader_managers: {list(trader_managers.keys())}")
            print(f"user_sessions: {user_sessions}")
            print(f"trader_to_session_lookup: {trader_to_session_lookup}")
            print(f"Traceback: {traceback.format_exc()}\n")
            raise HTTPException(
                status_code=500,
                detail=f"Error assigning trader to session: {str(e)}"
            )

async def send_to_frontend(websocket: WebSocket, trader_manager):
    while True:
        trading_session = trader_manager.trading_session
        time_update = {
            "type": "time_update",
            "data": {
                "current_time": trading_session.current_time.isoformat(),
                "is_trading_started": trading_session.trading_started,
                "remaining_time": (
                    trading_session.start_time
                    + timedelta(minutes=trading_session.duration)
                    - trading_session.current_time
                ).total_seconds()
                if trading_session.trading_started
                else None,
                "current_human_traders": len(trader_manager.human_traders),
                "expected_human_traders": trader_manager.params.num_human_traders,
            },
        }
        await websocket.send_json(time_update)
        await asyncio.sleep(1)

async def receive_from_frontend(websocket: WebSocket, trader):
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            parsed_message = json.loads(message)
            
            # only lock for orders
            if parsed_message.get('type') == 'order':
                async with trader_locks[trader.id]:
                    await trader.on_message_from_client(message)
            else:
                # other messages don't need locks
                await trader.on_message_from_client(message)
                
        except asyncio.TimeoutError:
            pass
        except WebSocketDisconnect:
            return
        except json.JSONDecodeError:
            pass
        except Exception as e:
            return

@app.get("/session_metrics")
async def get_session_metrics(trader_id: str, session_id: str, current_user: dict = Depends(get_current_user)):
    if trader_id != f"HUMAN_{current_user['gmail_username']}":
        raise HTTPException(status_code=403, detail="Unauthorized access to trader data")
    
    log_file_path = f"logs/{session_id}_trading.log"
    
    try:
        processed_data = process_log_file(log_file_path)
        
        output = io.StringIO()
        write_to_csv(processed_data, output)
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}_trader_{trader_id}_metrics.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing session metrics")


@app.websocket("/trader/{trader_id}")
async def websocket_trader_endpoint(websocket: WebSocket, trader_id: str):
    await websocket.accept()
    session_id = None
    try:
        token = await websocket.receive_text()
        decoded_token = custom_verify_id_token(token)
        email = decoded_token['email']
        gmail_username = extract_gmail_username(email)
        
        session_id = trader_to_session_lookup.get(trader_id)
        if not session_id:
            print(f"No active session found for trader {trader_id}")
            await websocket.close()
            return
            
        trader_manager = trader_managers[session_id]
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            print(f"Trader not found in session {session_id}")
            await websocket.close()
            return
        
        # track them
        active_users[session_id].add(gmail_username)
        user_sessions[gmail_username] = session_id
        
        # tell everyone the counts
        initial_count = {
            "type": "trader_count_update",
            "data": {
                "current_human_traders": len(active_users[session_id]),
                "expected_human_traders": trader_manager.params.num_human_traders,
                "session_id": session_id
            }
        }
        await websocket.send_json(initial_count)
        
        await trader.connect_to_socket(websocket)
        
        try:
            send_task = asyncio.create_task(send_to_frontend(websocket, trader_manager))
            receive_task = asyncio.create_task(receive_from_frontend(websocket, trader))
            
            done, pending = await asyncio.wait(
                [send_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
            
        except WebSocketDisconnect:
            pass
        finally:
            if session_id:
                # Only remove from active users, don't delete session
                if gmail_username in active_users[session_id]:
                    active_users[session_id].discard(gmail_username)
                await broadcast_trader_count(session_id)
            
    except Exception as e:
        if session_id:
            # Only remove from active users, don't delete session
            if gmail_username in active_users[session_id]:
                active_users[session_id].discard(gmail_username)
            await broadcast_trader_count(session_id)
        await websocket.close()

current_dir = Path(__file__).resolve().parent
ROOT_DIR = current_dir.parent / "logs"
print(f"ROOT_DIR is set to: {ROOT_DIR}")

@app.get("/files")
async def list_files(
    path: str = Query("", description="Relative path to browse")
):
    try:
        full_path = (ROOT_DIR / path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {full_path}")
        
        if full_path.is_file():
            return {"type": "file", "name": full_path.name}
        
        files = []
        directories = []
        
        for item in full_path.iterdir():
            if item.is_file():
                files.append({"type": "file", "name": item.name})
            elif item.is_dir():
                directories.append({"type": "directory", "name": item.name})
        
        return {
            "current_path": str(full_path.relative_to(ROOT_DIR)),
            "parent_path": str(full_path.parent.relative_to(ROOT_DIR)) if full_path != ROOT_DIR else None,
            "directories": directories,
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    try:
        full_path = (ROOT_DIR / file_path).resolve()
        
        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail=f"Access denied: {full_path} is not relative to {ROOT_DIR}")
        
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
        
        return FileResponse(full_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def broadcast_session_status(session_id: str):
    """tell everyone what's up with the session"""
    if session_id not in trader_managers:
        return
        
    trader_manager = trader_managers[session_id]
    ready_traders = session_ready_traders[session_id]
    expected_traders = trader_manager.params.num_human_traders
    all_ready = len(ready_traders) == expected_traders and len(active_users[session_id]) == expected_traders
    
    status_message = {
        "type": "session_status_update",
        "data": {
            "ready_count": len(ready_traders),
            "total_needed": expected_traders,
            "ready_traders": list(ready_traders),
            "all_ready": all_ready,
            "can_start": all_ready
        }
    }
    
    # tell everyone
    for trader in trader_manager.human_traders:
        if hasattr(trader, 'websocket') and trader.websocket:
            try:
                await trader.websocket.send_json(status_message)
            except Exception as e:
                logger.error(f"Error broadcasting to trader: {str(e)}")

# lets start trading!
@app.post("/trading/start")
async def start_trading_session(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    session_id = trader_to_session_lookup.get(trader_id)
    
    if not session_id:
        raise HTTPException(status_code=404, detail="No active session found for this user")
    
    trader_manager = trader_managers[session_id]
    
    # mark em ready
    session_ready_traders[session_id].add(gmail_username)
    
    # tell everyone whats up
    await broadcast_session_status(session_id)
    
    # check if we got everyone
    current_traders = active_users[session_id]
    expected_traders = trader_manager.params.num_human_traders
    all_ready = (len(session_ready_traders[session_id]) == expected_traders and 
                len(current_traders) == expected_traders)
    
    response_data = {
        "status": "success",
        "ready_count": len(session_ready_traders[session_id]),
        "total_needed": expected_traders,
        "all_ready": all_ready
    }
    
    # if everyones here, lets get this party started
    if all_ready:
        # hype message to get people ready
        start_message = {
            "type": "trading_starting",
            "data": {
                "message": "All traders ready. Trading session starting..."
            }
        }
        
        for trader in trader_manager.human_traders:
            if hasattr(trader, 'websocket') and trader.websocket:
                try:
                    await trader.websocket.send_json(start_message)
                except Exception as e:
                    logger.error(f"Error notifying trader of start: {str(e)}")
        
        background_tasks.add_task(trader_manager.launch)
        response_data["message"] = "Trading session started"
    else:
        response_data["message"] = f"Waiting for other traders ({len(session_ready_traders[session_id])}/{expected_traders} ready)"
    
    return response_data

# admin stuff - update the google form id
@app.post("/admin/update_google_form_id")
async def update_google_form_id_endpoint(new_form_id: str, current_user: dict = Depends(get_current_admin_user)):
    params = TradingParameters()
    params.google_form_id = new_form_id
    update_form_id(new_form_id)
    return {"status": "success", "message": "Google Form ID updated successfully"}

# refresh our user list
@app.get("/admin/refresh_registered_users")
async def refresh_registered_users(current_user: dict = Depends(get_current_admin_user)):
    get_registered_users(force_update=True)
    return {"status": "success", "message": "Registered users refreshed"}

# keep our user list fresh
async def periodic_update_registered_users():
    while True:
        try:
            form_id = TradingParameters().google_form_id
            get_registered_users(force_update=True, form_id=form_id)
        except ssl.SSLEOFError as e:
            logger.warning(f"SSL connection closed during periodic update: {str(e)}")
        except Exception as e:
            logger.error(f"Error during periodic update of registered users: {str(e)}")
        finally:
            # keep on truckin
            await asyncio.sleep(300)  # nap for 5 mins

# time offset calc loop
async def periodic_time_offset_calculation():
    while True:
        # nothing to do here anymore
        await asyncio.sleep(3600)  # snooze for an hour

# startup tasks
@app.on_event("startup")
async def startup_event():
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# peace out ✌️
@app.post("/user/logout")
async def user_logout(current_user: dict = Depends(get_current_user)):
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    if gmail_username in user_sessions:
        session_id = user_sessions[gmail_username]
        await remove_trader_from_session(trader_id, session_id)
        return {"status": "success", "message": "User logged out successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found in any active session")

# cleanup crew
async def cleanup(session_id: str):
    if session_id in active_users:
        for username in active_users[session_id]:
            if username in user_sessions:
                del user_sessions[username]
        del active_users[session_id]
    # ... (rest of the cleanup logic)

# what role you playin?
@app.get("/user/role")
async def get_user_role(current_user: dict = Depends(get_current_user)):
    gmail_username = current_user['gmail_username']
    goal = user_goals.get(gmail_username, None)
    
    role = "unknown"
    if goal is not None:
        if goal > 0:
            role = "buyer"
        elif goal < 0:
            role = "seller"
        else:
            role = "speculator"
            
    return {
        "status": "success",
        "data": {
            "username": gmail_username,
            "role": role,
            "goal": goal
        }
    }

# make sure everything looks good
@app.get("/session/validate/{session_id}")
async def validate_session(session_id: str, current_user: dict = Depends(get_current_admin_user)):
    """check if session is set up right"""
    if session_id not in trader_managers:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_traders = active_users[session_id]
    informed_trader = session_informed_traders.get(session_id)
    
    violations = []
    
    # need exactly one informed trader
    if not informed_trader:
        violations.append("Session has no informed trader")
    
    # make sure roles make sense
    for username in session_traders:
        if username in user_roles:
            role = user_roles[username]
            if role == 'informed' and username != informed_trader:
                violations.append(f"Multiple informed traders found: {username} and {informed_trader}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "violations": violations,
        "is_valid": len(violations) == 0
    }

# quick session check
def is_session_valid(session_id: str) -> bool:
    """is this session still kickin?"""
    if session_id not in trader_managers:
        return False
    
    trader_manager = trader_managers[session_id]
    return trader_manager.trading_session.active

# whats the status?
@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str, current_user: dict = Depends(get_current_user)):
    if session_id not in trader_managers:
        raise HTTPException(status_code=404, detail="Session not found")
        
    trader_manager = trader_managers[session_id]
    ready_traders = session_ready_traders[session_id]
    expected_traders = trader_manager.params.num_human_traders
    
    return {
        "status": "success",
        "data": {
            "ready_count": len(ready_traders),
            "total_needed": expected_traders,
            "ready_traders": list(ready_traders),
            "all_ready": len(ready_traders) == expected_traders
        }
    }

# nuke everything from orbit
@app.post("/admin/reset_state")
async def reset_state(current_user: dict = Depends(get_current_admin_user)):
    """start fresh"""
    try:
        print("\n=== Resetting Internal State ===")
        
        global user_goals, goal_assignments, user_historical_sessions
        
        # clear all the things
        user_goals.clear()
        goal_assignments.clear()
        user_historical_sessions.clear()
        
        # cleanup whatevers running
        for session_id in list(trader_managers.keys()):
            await cleanup_session(session_id, reason="admin_reset")
            
        # wipe the rest
        trader_managers.clear()
        trader_to_session_lookup.clear()
        active_users.clear()
        user_sessions.clear()
        session_ready_traders.clear()
        session_creation_times.clear()
        
        print("All internal state has been reset")
        print("=== Reset Complete ===\n")
        
        return {"status": "success", "message": "Internal state reset successfully"}
        
    except Exception as e:
        print(f"ERROR in reset_state: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting state: {str(e)}"
        )

# see ya later alligator
async def remove_trader_from_session(trader_id: str, session_id: str):
    """kick em out"""
    try:
        if session_id in trader_managers:
            trader_manager = trader_managers[session_id]
            
            # boot from manager
            if hasattr(trader_manager, 'remove_trader'):
                await trader_manager.remove_trader(trader_id)
            
            # unready them
            gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None
            if gmail_username and session_id in session_ready_traders:
                session_ready_traders[session_id].discard(gmail_username)
            
            # remove from active list
            if gmail_username and session_id in active_users:
                active_users[session_id].discard(gmail_username)
            
            # cleanup lookup
            if trader_id in trader_to_session_lookup:
                del trader_to_session_lookup[trader_id]
            
            # tell everyone whos left
            await broadcast_trader_count(session_id)
            
            # update the status
            await broadcast_session_status(session_id)
            
            # if nobodys home, shut it down
            if len(active_users.get(session_id, set())) == 0:
                await cleanup_session(session_id, reason="no_active_traders")
                
    except Exception as e:
        logger.error(f"Error removing trader from session: {str(e)}")

# headcount!
async def broadcast_trader_count(session_id: str):
    """whos still here?"""
    if session_id not in trader_managers:
        return
        
    trader_manager = trader_managers[session_id]
    current_traders = len(active_users[session_id])
    expected_traders = trader_manager.params.num_human_traders
    
    count_message = {
        "type": "trader_count_update",
        "data": {
            "current_human_traders": current_traders,
            "expected_human_traders": expected_traders,
            "session_id": session_id
        }
    }
    
    print(f"Broadcasting trader count for session {session_id}: {current_traders}/{expected_traders}")
    
    # spread the word
    for trader in trader_manager.human_traders:
        if hasattr(trader, 'websocket') and trader.websocket:
            try:
                await trader.websocket.send_json(count_message)
            except Exception as e:
                logger.error(f"Error broadcasting trader count: {str(e)}")

# update the things
async def update_session_state(session_id: str, updates: dict):
    """change stuff safely"""
    try:
        if session_id not in trader_managers:
            return False
            
        # lock it down
        async with session_locks[session_id]:
            trader_manager = trader_managers[session_id]
            
            # update whos ready
            if 'ready_traders' in updates:
                ready_traders = updates['ready_traders']
                session_ready_traders[session_id] = set(ready_traders)
            
            # update whos here
            if 'active_users' in updates:
                active_users[session_id] = set(updates['active_users'])
        
        # handle the lookups
        if 'trader_lookups' in updates:
            for trader_id, lookup_session_id in updates['trader_lookups'].items():
                async with trader_locks[trader_id]:
                    trader_to_session_lookup[trader_id] = lookup_session_id
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating session state: {str(e)}")
        return False
