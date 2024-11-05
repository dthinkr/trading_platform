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
from core.session_handler import SessionHandler
from core.data_models import TraderType, TradingParameters, UserRegistration, TraderRole
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
    allow_headers=["*", "Authorization"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

session_handler = SessionHandler()
trader_managers = {}
persistent_settings = {}

# helper funcs
def get_historical_sessions_count(username):
    return len(session_handler.user_historical_sessions[username])

def record_session_for_user(username, session_id):
    session_handler.user_historical_sessions[username].add(session_id)

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
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication method"
            )
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            decoded_token = auth.verify_id_token(token, check_revoked=True)
        except Exception as auth_error:
            logger.error(f"Firebase auth error: {str(auth_error)}")
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(auth_error)}"
            )
            
        email = decoded_token['email']
        gmail_username = extract_gmail_username(email)
        
        # Check registration
        form_id = TradingParameters().google_form_id
        if not is_user_registered(email, form_id):
            raise HTTPException(
                status_code=403, 
                detail="User not registered in the study"
            )
        
        # Create parameters
        params = TradingParameters(**(persistent_settings or {}))
        
        # Single call to handle all session/role/goal logic
        session_id, trader_id, role, goal = await session_handler.validate_and_assign_role(
            gmail_username, 
            params
        )
        
        return {
            "status": "success",
            "message": "Login successful and trader assigned",
            "data": {
                "username": email,
                "is_admin": is_user_admin(email),
                "session_id": session_id,
                "trader_id": trader_id,
                "role": role,
                "goal": goal
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

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
    try:
        print("\n=== Trading Session Initiation ===")
        print(f"Current user: {current_user}")
        print(f"Persistent settings: {persistent_settings}")
        
        try:
            merged_params = TradingParameters(**(persistent_settings or {}))
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
        
        # Use session_handler instead of global variable
        trader_manager = session_handler.get_trader_manager(trader_id)
        if not trader_manager:
            print("No active session found for this user")
            raise HTTPException(status_code=404, detail="No active session found for this user")
        
        session_id = session_handler.trader_to_session_lookup.get(trader_id)
        print(f"Found session_id: {session_id}")
        
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
    """Get the trader manager for a given trader ID"""
    if trader_id not in session_handler.trader_to_session_lookup:
        return None
    trading_session_id = session_handler.trader_to_session_lookup[trader_id]
    manager = session_handler.trader_managers.get(trading_session_id)  # Use session_handler instead of global trader_managers
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
        historical_sessions_count = len(session_handler.user_historical_sessions.get(gmail_username, set()))
        
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
        session_id = session_handler.trader_to_session_lookup.get(trader_id)
        
        # get their trading history
        log_file_path = os.path.join("logs", f"{session_id}_trading.log")
        
        try:
            order_book_metrics = order_book_contruction(log_file_path)
            
            # just their stuff
            trader_specific_metrics = order_book_metrics.get(f"'{trader_id}'", {})
            
            # everyone else's stuff
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
    # Use session_handler instead of global variables
    trader_manager = session_handler.get_trader_manager(trader_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="No session found for this trader")

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
                tid for tid, sid in session_handler.trader_to_session_lookup.items() 
                if sid == session_id
            ]
            for trader_id in traders_to_remove:
                del session_handler.trader_to_session_lookup[trader_id]
                
            return True
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            return False

# Add these to the global state variables at the top
ROLE_INFORMED = "informed"
ROLE_SPECULATOR = "speculator"
session_informed_roles = {}  # session_id -> username of informed trader

# Add this function near the top with other helper functions
async def determine_trader_role(gmail_username: str) -> TraderRole:
    """Determine role for a trader before session assignment"""
    # Check if they already have a historical role
    historical_role = user_roles.get(gmail_username)
    if historical_role:
        return historical_role
        
    # Get their session count
    historical_sessions = len(session_handler.user_historical_sessions.get(gmail_username, set()))
    
    # First-time traders have equal chance of being informed/speculator
    if historical_sessions == 0:
        role = random.choice([TraderRole.INFORMED, TraderRole.SPECULATOR])
    else:
        # Subsequent sessions alternate roles
        last_role = user_roles.get(gmail_username)
        if last_role == TraderRole.INFORMED:
            role = TraderRole.SPECULATOR
        else:
            role = TraderRole.INFORMED
            
    # Remember their role
    user_roles[gmail_username] = role
    return role

async def find_or_create_session_and_assign_trader(gmail_username):
    async with session_assignment_lock:
        try:
            print(f"\n=== Starting session assignment for {gmail_username} ===")
            print(f"Current trader_managers: {list(session_handler.trader_managers.keys())}")
            print(f"Current user_sessions: {session_handler.user_sessions}")
            print(f"Current trader_to_session_lookup: {session_handler.trader_to_session_lookup}")
            
            if gmail_username in session_handler.user_sessions:
                session_id = session_handler.user_sessions[gmail_username]
                trader_id = f"HUMAN_{gmail_username}"
                
                if session_id in session_handler.trader_managers:
                    trader_manager = session_handler.trader_managers[session_id]
                    if not trader_manager.trading_session.trading_started:
                        print(f"User rejoining session: {session_id}")
                        session_handler.active_users[session_id].add(gmail_username)
                        session_handler.trader_to_session_lookup[trader_id] = session_id
                        return session_id, trader_id
                
                print(f"Cleaning up invalid session reference: {session_id}")
                del session_handler.user_sessions[gmail_username]
                if trader_id in session_handler.trader_to_session_lookup:
                    del session_handler.trader_to_session_lookup[trader_id]

            # determine role before assigning a session
            role = await session_handler.determine_user_role(gmail_username)
            print(f"Determined role for {gmail_username}: {role}")

            attempts = 5
            
            for attempt in range(attempts):
                print(f"Looking for available session (attempt {attempt + 1}/{attempts})")
                
                for session_id, manager in session_handler.trader_managers.items():
                    current_traders = len(session_handler.active_users[session_id])
                    expected_traders = manager.params.num_human_traders
                    
                    if current_traders >= expected_traders or manager.trading_session.trading_started:
                        continue

                    if role == TraderRole.INFORMED:
                        if manager.informed_trader is not None:
                            continue
                    else:
                        if manager.informed_trader is None and current_traders == expected_traders - 1:
                            continue
                    
                    print(f"Found suitable session: {session_id}")
                    trader_id = await manager.add_human_trader(gmail_username, role=role)
                    
                    session_handler.trader_to_session_lookup[trader_id] = session_id
                    session_handler.active_users[session_id].add(gmail_username)
                    session_handler.user_sessions[gmail_username] = session_id
                    
                    return session_id, trader_id
                
                if attempt < attempts - 1:
                    print(f"No suitable session found, waiting before attempt {attempt + 2}/{attempts}")
                    await sleep(0.5)

            print("No suitable session found after waiting, creating new session")
            params = TradingParameters(**persistent_settings)
            new_trader_manager = TraderManager(params)
            session_id = new_trader_manager.trading_session.id
            session_handler.trader_managers[session_id] = new_trader_manager  # Use session_handler
            
            trader_id = await new_trader_manager.add_human_trader(gmail_username, role=role)
            
            session_handler.trader_to_session_lookup[trader_id] = session_id
            session_handler.active_users[session_id] = set([gmail_username])  # Initialize the set
            session_handler.user_sessions[gmail_username] = session_id
            
            return session_id, trader_id

        except Exception as e:
            print(f"Error in session assignment: {str(e)}")
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
        
        trader_manager = session_handler.get_trader_manager(trader_id)
        if not trader_manager:
            print(f"No active session found for trader {trader_id}")
            await websocket.close()
            return
            
        session_id = session_handler.trader_to_session_lookup.get(trader_id)
        trader = trader_manager.get_trader(trader_id)
        if not trader:
            print(f"Trader not found in session {session_id}")
            await websocket.close()
            return
        
        # track them
        session_handler.active_users[session_id].add(gmail_username)
        session_handler.user_sessions[gmail_username] = session_id
        
        # tell everyone the counts
        initial_count = {
            "type": "trader_count_update",
            "data": {
                "current_human_traders": len(session_handler.active_users[session_id]),
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
                session_handler.active_users[session_id].discard(gmail_username)
                await broadcast_trader_count(session_id)
            
    except Exception as e:
        if session_id:
            session_handler.active_users[session_id].discard(gmail_username)
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
    status = session_manager.get_session_status(session_id)
    if not status:
        return
        
    status_message = {
        "type": "session_status_update",
        "data": status
    }
    
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
    
    # Get session from session_handler
    session_id = session_handler.trader_to_session_lookup.get(trader_id)
    if not session_id:
        raise HTTPException(status_code=404, detail="No active session found")
    
    # Mark trader ready
    all_ready = await session_handler.mark_trader_ready(trader_id, session_id)
    
    # Get trader manager
    trader_manager = session_handler.trader_managers.get(session_id)
    if not trader_manager:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get current status
    current_ready = len(session_handler.session_ready_traders.get(session_id, set()))
    total_needed = trader_manager.params.num_human_traders
    
    status = {
        "ready_count": current_ready,
        "total_needed": total_needed,
        "ready_traders": list(session_handler.session_ready_traders.get(session_id, set())),
        "all_ready": all_ready
    }
    
    if all_ready:
        background_tasks.add_task(trader_manager.launch)
        status["message"] = "Trading session started"
    else:
        status["message"] = f"Waiting for other traders ({current_ready}/{total_needed} ready)"
    
    return status

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

# Update validate_session
@app.get("/session/validate/{session_id}")
async def validate_session(session_id: str, current_user: dict = Depends(get_current_admin_user)):
    """check if session is set up right"""
    session = session_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    violations = []
    
    # Check for informed trader
    if not session.informed_trader:
        violations.append("Session has no informed trader")
    
    # Check for role consistency
    for username in session.active_users:
        user = session_manager.get_user_state(username)
        if user.current_role == TraderRole.INFORMED and username != session.informed_trader:
            violations.append(f"Multiple informed traders found: {username} and {session.informed_trader}")
    
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
    try:
        # Reset session manager
        await session_manager.reset_state()
        
        # Clean up trader managers
        for session_id in list(trader_managers.keys()):
            trader_manager = trader_managers[session_id]
            await trader_manager.cleanup()
            
        trader_managers.clear()
        
        return {"status": "success", "message": "Internal state reset successfully"}
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting state: {str(e)}")

# see ya later alligator
async def remove_trader_from_session(trader_id: str, session_id: str):
    """kick em out"""
    try:
        gmail_username = trader_id.split("HUMAN_")[-1] if trader_id.startswith("HUMAN_") else None
        if not gmail_username:
            return
            
        # Remove from session manager
        await session_manager.remove_user_from_session(gmail_username, session_id)
        
        # Remove from trader manager
        if session_id in trader_managers:
            trader_manager = trader_managers[session_id]
            if hasattr(trader_manager, 'remove_trader'):
                await trader_manager.remove_trader(trader_id)
        
        # Update everyone
        await broadcast_session_status(session_id)
        
        # Check if session should be cleaned up
        session = session_manager.sessions.get(session_id)
        if session and not session.active_users:
            await session_manager.cleanup_session(session_id)
            if session_id in trader_managers:
                await trader_managers[session_id].cleanup()
                del trader_managers[session_id]
                
    except Exception as e:
        logger.error(f"Error removing trader from session: {str(e)}")
        
# headcount!
async def broadcast_trader_count(session_id: str):
    """whos still here?"""
    trader_manager = session_handler.trader_managers.get(session_id)
    if not trader_manager:
        return
        
    current_traders = len(session_handler.active_users[session_id])
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
                    session_handler.trader_to_session_lookup[trader_id] = lookup_session_id
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating session state: {str(e)}")
        return False

# Add these headers to every response
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response
