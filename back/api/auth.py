import os
from functools import lru_cache
from fastapi import Depends, HTTPException, status, Request, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
import firebase_admin
from firebase_admin import credentials, auth
import secrets
import time
from .google_sheet_auth import is_user_registered, is_user_admin, update_form_id
from core.data_models import TradingParameters
from pytz import timezone
from datetime import datetime
import jwt
from .prolific_auth import extract_prolific_params, authenticate_prolific_user, get_prolific_user_by_trader_id, prolific_tokens

# Initialize Firebase Admin SDK using the service account file
cred = credentials.Certificate('firebase-service-account.json')
firebase_admin.initialize_app(cred)

security = HTTPBearer()
basic_auth = HTTPBasic()

@lru_cache()
def get_firebase_auth():
    return auth

# Store authenticated users
authenticated_users = {}

def extract_gmail_username(email):
    return email.split('@')[0] if '@' in email else email

def get_user_timezone(user_timezone_str):
    try:
        return timezone(user_timezone_str)
    except:
        return timezone('UTC')  # Default to UTC if timezone is invalid

def custom_verify_id_token(token, clock_skew_seconds=60):
    try:
        # Decode the token without verifying it first
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        current_time = int(time.time())
        token_issued_at = decoded_token.get('iat', 0)
        token_expiry = decoded_token.get('exp', 0)
        
        # Check if the token is within the acceptable time range
        if token_issued_at - clock_skew_seconds > current_time:
            raise jwt.InvalidTokenError("Token used too early")
        
        if current_time > token_expiry + clock_skew_seconds:
            raise jwt.ExpiredSignatureError("Token has expired")
        
        # If time checks pass, verify the token with Firebase
        return auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=clock_skew_seconds)
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

async def get_current_user(request: Request):
    # First, check for Prolific authentication via URL parameters
    prolific_params = await extract_prolific_params(request)
    if prolific_params:
        try:
            # Use the new authenticate_prolific_user function for consistent authentication
            prolific_user = await authenticate_prolific_user(request)
            if prolific_user:
                # Store the prolific user in authenticated_users
                authenticated_users[prolific_user['gmail_username']] = prolific_user
                print(f"Authenticated Prolific user via params: {prolific_user['gmail_username']}")
                return prolific_user
        except HTTPException:
            # If authentication fails, continue with other methods
            pass
    
    # Check if this is a request for a specific trader
    path = request.url.path
    
    # Handle trader-specific paths
    trader_id = None
    if path.startswith("/trader/"):
        # Format: /trader/HUMAN_username/...
        parts = path.split("/")
        if len(parts) > 2:
            trader_id = parts[2]  # Get the HUMAN_username part
    elif path.startswith("/trader_info/"):
        # Format: /trader_info/HUMAN_username
        trader_id = path.split("/")[-1]
    
    # Check if this is a Prolific user by trader_id
    if trader_id:
        prolific_user = get_prolific_user_by_trader_id(trader_id)
        if prolific_user:
            print(f"Found Prolific user by trader_id: {trader_id}")
            return prolific_user
        
        # If not a Prolific user but we have it in authenticated_users
        if trader_id.startswith("HUMAN_"):
            gmail_username = trader_id.split('_')[1]
            if gmail_username in authenticated_users:
                print(f"Found authenticated user by trader_id: {trader_id}")
                return authenticated_users[gmail_username]
    
    # If not a Prolific user, proceed with regular authentication
    auth_header = request.headers.get('Authorization')
    user_timezone_str = request.headers.get('X-User-Timezone', 'UTC')
    user_timezone = get_user_timezone(user_timezone_str)
    
    # Check for Prolific authentication in headers
    if auth_header and auth_header.startswith('Prolific '):
        token = auth_header.split('Prolific ')[1]
        if token in prolific_tokens:
            print(f"Authenticated via Prolific token: {token}")
            return prolific_tokens[token]
    
    # For endpoints that commonly fail with Prolific users
    if path.startswith("/trading/initiate") or "/trader/" in path or path.startswith("/trading/start"):
        # Check if we can find a Prolific user for this request
        if trader_id:
            prolific_user = get_prolific_user_by_trader_id(trader_id)
            if prolific_user:
                print(f"Special case: Found Prolific user for {path}: {trader_id}")
                return prolific_user
        
        # If we have Prolific users in the system, use the first one as a fallback
        # This is a temporary solution to ensure Prolific users can access these endpoints
        if prolific_tokens and not auth_header:
            first_token = next(iter(prolific_tokens))
            print(f"Fallback: Using first available Prolific user for {path}")
            return prolific_tokens[first_token]
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Authorization header found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if auth_header.startswith('Basic '):
        credentials = HTTPBasicCredentials.parse(auth_header)
        correct_username = secrets.compare_digest(credentials.username, "admin")
        correct_password = secrets.compare_digest(credentials.password, "admin")
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect admin credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return {"username": "admin", "is_admin": True, "timezone": user_timezone}
    
    elif auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
        try:
            decoded_token = custom_verify_id_token(token)
            
            email = decoded_token['email']
            gmail_username = extract_gmail_username(email)
            
            # First check if user is admin
            is_admin = is_user_admin(email)
            
            # Only check registration if not admin
            if not is_admin:
                form_id = TradingParameters().google_form_id
                if not is_user_registered(email, form_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User not registered in the study",
                    )
            
            user = {**decoded_token, "is_admin": is_admin, "gmail_username": gmail_username, "timezone": user_timezone}
            authenticated_users[gmail_username] = user
            print(f"Authenticated Google user: {gmail_username}")
            return user
        except Exception as e:
            # One last check for Prolific users
            if trader_id:
                prolific_user = get_prolific_user_by_trader_id(trader_id)
                if prolific_user:
                    print(f"Exception handler: Found Prolific user by trader_id: {trader_id}")
                    return prolific_user
                    
            # If we couldn't find a Prolific user, raise the original exception
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token or user not registered: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication method",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get('is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

def update_google_form_id(new_form_id: str):
    update_form_id(new_form_id)

def get_user_local_time(user):
    return datetime.now(user['timezone'])
