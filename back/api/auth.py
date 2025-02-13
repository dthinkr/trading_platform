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
from datetime import datetime, timedelta
import jwt

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
    auth_header = request.headers.get('Authorization')
    user_timezone_str = request.headers.get('X-User-Timezone', 'UTC')
    user_timezone = get_user_timezone(user_timezone_str)
    
    path = request.url.path
    if path.startswith("/trader_info/"):
        trader_id = path.split("/")[-1]
        gmail_username = trader_id.split('_')[1]
        if gmail_username in authenticated_users:
            return authenticated_users[gmail_username]
    
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
            return user
        except Exception as e:
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
