import asyncio
import io
from datetime import timedelta, datetime
from uuid import UUID, uuid4

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
from core.trader_manager import TraderManager
from core.data_models import TraderType, TradingParameters, UserRegistration
from .auth import get_current_user, get_current_admin_user, get_firebase_auth, extract_gmail_username, is_user_registered, is_user_admin, update_google_form_id, custom_verify_id_token
from .calculate_metrics import process_log_file, write_to_csv
from .logfiles_analysis import order_book_contruction, is_jsonable, calculate_trader_specific_metrics
from firebase_admin import auth
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

logger = setup_custom_logger(__name__)

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

trader_managers = {}
trader_to_session_lookup = {}
trader_manager: TraderManager = None

persistent_settings = {}

active_users = defaultdict(set)  # Maps session_id to set of active usernames
user_sessions = {}  # Maps username to their current session_id

# Add this near the top of the file, with other global variables
user_historical_sessions = defaultdict(set)

# Add these near the top with other global variables
user_roles = {}  # Maps username to their assigned role ('informed' or 'speculator')
session_informed_traders = defaultdict(str)  # Maps session_id to its informed trader's username

# Add near the top with other globals
session_creation_times = {}  # Maps session_id to its creation timestamp
SESSION_TIMEOUT = 60  # Timeout in seconds

# Add this near the top with other global variables
session_ready_traders = defaultdict(set)  # Maps session_id to set of ready traders

# Add these near the top with other global variables
user_goals = {}  # Maps username to their assigned goal
goal_assignments = {}  # Maps session_id to list of already assigned goal indices

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
        
        # Add clock_skew_seconds parameter here as well
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        email = decoded_token['email']
        
        form_id = TradingParameters().google_form_id
        if not is_user_registered(email, form_id):
            raise HTTPException(status_code=403, detail="User not registered in the study")
        
        gmail_username = extract_gmail_username(email)
        
        # Check if the user is an admin
        is_admin = is_user_admin(email)
        
        # Check if the user has exceeded the maximum number of historical sessions (skip for admins)
        if not is_admin:
            historical_sessions_count = get_historical_sessions_count(gmail_username)
            if historical_sessions_count >= persistent_settings.get('max_sessions_per_human', 4):
                raise HTTPException(status_code=403, detail="Maximum number of allowed sessions reached for this user")
        
        session_id, trader_id = await find_or_create_session_and_assign_trader(gmail_username)
        
        # Add user to active users for this session
        active_users[session_id].add(gmail_username)
        user_sessions[gmail_username] = session_id
        
        # Record this session in the user's historical sessions
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
    """Helper function to get trader info with additional session data"""
    try:
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail="Trader not found")
        
        # Get base trader attributes
        trader_data = trader.get_trader_params_as_dict()
        
        # Initialize all_attributes if it doesn't exist
        if 'all_attributes' not in trader_data:
            trader_data['all_attributes'] = {}
            
        # Extract gmail username from trader_id (format is "HUMAN_gmail_username")
        gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None
        
        # Get historical sessions count from the global tracking
        historical_sessions_count = len(user_historical_sessions.get(gmail_username, set()))
        
        # Get trading parameters
        params = trader_manager.params.model_dump() if trader_manager.params else {}
        
        # Check if user is admin (safely get admin_users list)
        admin_users = params.get('admin_users', [])
        is_admin = gmail_username in admin_users if gmail_username else False
        
        # Add additional attributes
        trader_data['all_attributes'].update({
            'historical_sessions_count': historical_sessions_count,
            'is_admin': is_admin,
            'params': params
        })
        
        # Add basic trader info if not present
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
        # Use the new helper function to get enhanced trader info
        trader_data = get_trader_info_with_session_data(trader_manager, trader_id)
        
        # Get the session ID for this trader
        session_id = trader_to_session_lookup.get(trader_id)
        
        # Get the order book metrics
        log_file_path = os.path.join("logs", f"{session_id}_trading.log")
        
        try:
            order_book_metrics = order_book_contruction(log_file_path)
            
            # Extract the specific trader's metrics
            trader_specific_metrics = order_book_metrics.get(f"'{trader_id}'", {})
            
            # Remove the trader-specific metrics from the general metrics
            general_metrics = {k: v for k, v in order_book_metrics.items() if k != f"'{trader_id}'"}

            # Calculate trader-specific metrics
            if trader_specific_metrics:
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
                **trader_data,  # This includes goal and goal_progress from get_trader_params_as_dict()
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
    """Check if a session has timed out and clean it up if necessary"""
    if session_id not in session_creation_times:
        return False
    
    elapsed_time = time.time() - session_creation_times[session_id]
    if elapsed_time > SESSION_TIMEOUT and not trader_managers[session_id].trading_session.trading_started:
        print(f"Session {session_id} timed out after {elapsed_time:.1f} seconds")
        await cleanup_session(session_id, reason="timeout")
        return True
    return False

async def cleanup_session(session_id: str, reason: str = "normal"):
    """Clean up a session and notify its users"""
    if session_id in trader_managers:
        trader_manager = trader_managers[session_id]
        
        # Notify all connected traders about the cleanup
        for trader in trader_manager.human_traders:
            if hasattr(trader, 'websocket') and trader.websocket:
                try:
                    if not trader.websocket.application_state.name == "DISCONNECTED":
                        await trader.websocket.send_json({
                            "type": "SESSION_TERMINATED",
                            "reason": reason,
                            "message": "Session terminated due to normal cleanup"
                        })
                except Exception as e:
                    logger.error(f"Error notifying trader during cleanup: {str(e)}")
                    continue

        try:
            # Clean up session data
            await trader_manager.cleanup()
            del trader_managers[session_id]
            
            # Clean up tracking dictionaries
            if session_id in goal_assignments:
                del goal_assignments[session_id]
                
            # Update user tracking
            for username in list(active_users[session_id]):
                if username in user_sessions:
                    del user_sessions[username]
            if session_id in active_users:
                del active_users[session_id]
                
            if session_id in session_ready_traders:
                del session_ready_traders[session_id]
                
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            return False
            
        return True

async def find_or_create_session_and_assign_trader(gmail_username):
    try:
        print(f"\n=== Starting session assignment for {gmail_username} ===")
        
        # First check if user already has an assigned goal
        existing_goal = user_goals.get(gmail_username)
        
        # Try to find an available session
        available_session = None
        available_session_id = None
        
        for session_id, manager in trader_managers.items():
            if len(manager.human_traders) < manager.params.num_human_traders:
                available_session = manager
                available_session_id = session_id
                print(f"Found available session: {session_id}")
                break

        # If no available session found, create a new one
        if not available_session:
            print("No available session found, creating new one")
            params = TradingParameters(**persistent_settings)
            new_trader_manager = TraderManager(params)
            
            session_id = new_trader_manager.trading_session.id
            trader_managers[session_id] = new_trader_manager
            session_creation_times[session_id] = time.time()
            available_session = new_trader_manager
            available_session_id = session_id
            goal_assignments[session_id] = []
            print(f"Created new session: {session_id}")

        # Handle goal assignment
        if existing_goal is None:
            # First time assignment - pick a role (abs value) from predefined goals
            assigned_indices = goal_assignments[available_session_id]
            available_indices = [i for i in range(len(available_session.params.predefined_goals)) 
                               if i not in assigned_indices]
            
            if not available_indices:
                raise HTTPException(
                    status_code=400,
                    detail="No available roles in this session"
                )
                
            next_index = available_indices[0]
            base_goal = available_session.params.predefined_goals[next_index]
            goal_assignments[available_session_id].append(next_index)
            
            # Store the absolute value of the goal for this user
            user_goals[gmail_username] = abs(base_goal)
            goal = base_goal  # For first assignment, use the predefined goal as is
            
        else:
            # User already has a role (abs value)
            abs_goal = user_goals[gmail_username]
            if abs_goal == 0:
                # Speculator (0) stays as 0
                goal = 0
            else:
                # Non-zero goals can flip sign if random assignment is enabled
                if available_session.params.allow_random_goals:
                    goal = abs_goal * random.choice([-1, 1])
                else:
                    goal = abs_goal  # Keep the original sign if random assignment is disabled
        
        print(f"Assigned goal {goal} to {gmail_username} (abs value: {user_goals[gmail_username]})")
        
        # Add trader to session with goal
        trader_id = await available_session.add_human_trader(gmail_username, goal=goal)
        
        # Update tracking dictionaries
        trader_to_session_lookup[trader_id] = available_session_id
        user_sessions[gmail_username] = available_session_id
        active_users[available_session_id].add(gmail_username)
        
        print(f"Final session state:")
        print(f"- Active users in session: {active_users[available_session_id]}")
        print(f"- User goals: {user_goals}")
        print(f"- Goal assignments for session: {goal_assignments[available_session_id]}")
        print("=== Session assignment complete ===\n")
        
        return available_session_id, trader_id
        
    except Exception as e:
        print(f"ERROR in session assignment: {str(e)}")
        logger.error(f"Error in find_or_create_session_and_assign_trader: {str(e)}")
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
            raise HTTPException(status_code=404, detail="No active session found for this trader")
            
        trader_manager = trader_managers[session_id]
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail="Trader not found in session")
        
        # Update active users
        active_users[session_id].add(gmail_username)
        user_sessions[gmail_username] = session_id
        
        # Send initial counts immediately after connection
        initial_count = {
            "type": "trader_count_update",
            "data": {
                "current_human_traders": len(active_users[session_id]),
                "expected_human_traders": trader_manager.params.num_human_traders,
                "session_id": session_id
            }
        }
        await websocket.send_json(initial_count)
        
        # Then broadcast to all traders
        await broadcast_trader_count(session_id)
        await broadcast_session_status(session_id)
        
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
                await remove_trader_from_session(trader_id, session_id)
            
    except Exception as e:
        if session_id:
            await remove_trader_from_session(trader_id, session_id)
        await websocket.send_json({
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "data": {}
        })
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

# Add this near the top with other global variables
async def broadcast_session_status(session_id: str):
    """Broadcast session status to all traders in the session"""
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
    
    # Broadcast to all traders in the session
    for trader in trader_manager.human_traders:
        if hasattr(trader, 'websocket') and trader.websocket:
            try:
                await trader.websocket.send_json(status_message)
            except Exception as e:
                logger.error(f"Error broadcasting to trader: {str(e)}")

# Modify the start_trading_session endpoint
@app.post("/trading/start")
async def start_trading_session(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    gmail_username = current_user['gmail_username']
    trader_id = f"HUMAN_{gmail_username}"
    
    session_id = trader_to_session_lookup.get(trader_id)
    
    if not session_id:
        raise HTTPException(status_code=404, detail="No active session found for this user")
    
    trader_manager = trader_managers[session_id]
    
    # Mark this trader as ready
    session_ready_traders[session_id].add(gmail_username)
    
    # Broadcast updated status to all traders
    await broadcast_session_status(session_id)
    
    # Check if all traders in the session are ready
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
    
    # Only start trading if we have all expected traders and they're all ready
    if all_ready:
        # Notify all traders that trading is starting
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

@app.post("/admin/update_google_form_id")
async def update_google_form_id_endpoint(new_form_id: str, current_user: dict = Depends(get_current_admin_user)):
    params = TradingParameters()
    params.google_form_id = new_form_id
    update_form_id(new_form_id)
    return {"status": "success", "message": "Google Form ID updated successfully"}

@app.get("/admin/refresh_registered_users")
async def refresh_registered_users(current_user: dict = Depends(get_current_admin_user)):
    get_registered_users(force_update=True)
    return {"status": "success", "message": "Registered users refreshed"}

# Add a background task to periodically update registered users
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
            # Continue the loop regardless of errors
            await asyncio.sleep(300)  # Sleep for 5 minutes before next update

async def periodic_time_offset_calculation():
    while True:
        # Remove the calculate_time_offset() call
        await asyncio.sleep(3600)  # Sleep for an hour

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_update_registered_users())
    asyncio.create_task(periodic_time_offset_calculation())

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

# Add a new endpoint to handle user logout
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

# Modify the cleanup function to remove users from active sessions
async def cleanup(session_id: str):
    if session_id in active_users:
        for username in active_users[session_id]:
            if username in user_sessions:
                del user_sessions[username]
        del active_users[session_id]
    # ... (rest of the cleanup logic)

# Update get_user_role endpoint to use goals
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

# Add validation endpoint
@app.get("/session/validate/{session_id}")
async def validate_session(session_id: str, current_user: dict = Depends(get_current_admin_user)):
    """Validate session conditions"""
    if session_id not in trader_managers:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_traders = active_users[session_id]
    informed_trader = session_informed_traders.get(session_id)
    
    violations = []
    
    # Check for exactly one informed trader
    if not informed_trader:
        violations.append("Session has no informed trader")
    
    # Check role consistency
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

# Add a helper function to check session validity
def is_session_valid(session_id: str) -> bool:
    """Check if a session exists and is still active"""
    if session_id not in trader_managers:
        return False
    
    trader_manager = trader_managers[session_id]
    return trader_manager.trading_session.active

# Add this new endpoint to check session status
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

@app.post("/admin/reset_state")
async def reset_state(current_user: dict = Depends(get_current_admin_user)):
    """Reset all internal state variables to default"""
    try:
        print("\n=== Resetting Internal State ===")
        
        global user_goals, goal_assignments, user_historical_sessions
        
        # Clear all tracking dictionaries
        user_goals.clear()
        goal_assignments.clear()
        user_historical_sessions.clear()
        
        # Clean up all active sessions
        for session_id in list(trader_managers.keys()):
            await cleanup_session(session_id, reason="admin_reset")
            
        # Clear remaining global state
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

# Add this new helper function
async def remove_trader_from_session(trader_id: str, session_id: str):
    """Remove a trader from a session and update counts"""
    try:
        if session_id in trader_managers:
            trader_manager = trader_managers[session_id]
            
            # Remove trader from manager
            if hasattr(trader_manager, 'remove_trader'):
                await trader_manager.remove_trader(trader_id)
            
            # Remove from ready traders if present
            gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None
            if gmail_username and session_id in session_ready_traders:
                session_ready_traders[session_id].discard(gmail_username)
            
            # Remove from active users
            if gmail_username and session_id in active_users:
                active_users[session_id].discard(gmail_username)
            
            # Clean up trader lookup
            if trader_id in trader_to_session_lookup:
                del trader_to_session_lookup[trader_id]
            
            # Immediately broadcast updated trader count
            await broadcast_trader_count(session_id)
            
            # Then broadcast session status
            await broadcast_session_status(session_id)
            
            # If no traders left, clean up session
            if len(active_users.get(session_id, set())) == 0:
                await cleanup_session(session_id, reason="no_active_traders")
                
    except Exception as e:
        logger.error(f"Error removing trader from session: {str(e)}")

# Add this function near the top with other helper functions
async def broadcast_trader_count(session_id: str):
    """Broadcast current trader count to all traders in the session"""
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
            "session_id": session_id  # Add session ID for verification
        }
    }
    
    # Log the counts being broadcast
    print(f"Broadcasting trader count for session {session_id}: {current_traders}/{expected_traders}")
    
    # Broadcast to all connected traders
    for trader in trader_manager.human_traders:
        if hasattr(trader, 'websocket') and trader.websocket:
            try:
                await trader.websocket.send_json(count_message)
            except Exception as e:
                logger.error(f"Error broadcasting trader count: {str(e)}")




