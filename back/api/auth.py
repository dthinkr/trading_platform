import os
from functools import lru_cache
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
import firebase_admin
from firebase_admin import credentials, auth
import secrets
import time

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

# Add a new function to extract Gmail username
def extract_gmail_username(email):
    return email.split('@')[0] if '@' in email else email

async def get_current_user(request: Request):
    auth_header = request.headers.get('Authorization')
    
    # Check if it's a request for trader info
    path = request.url.path
    if path.startswith("/trader_info/"):
        trader_id = path.split("/")[-1]
        # Update this line to use Gmail username instead of uid
        gmail_username = trader_id.split('_')[1]  # Assuming trader_id format is now "HUMAN_gmailusername"
        if gmail_username in authenticated_users:
            return authenticated_users[gmail_username]
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Authorization header found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if auth_header.startswith('Basic '):
        # Admin authentication (unchanged)
        credentials = HTTPBasicCredentials.parse(auth_header)
        correct_username = secrets.compare_digest(credentials.username, "admin")
        correct_password = secrets.compare_digest(credentials.password, "admin")
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect admin credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return {"username": "admin", "is_admin": True}
    
    elif auth_header.startswith('Bearer '):
        # Firebase authentication
        firebase_auth = get_firebase_auth()
        token = auth_header.split('Bearer ')[1]
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            email = decoded_token['email']
            gmail_username = extract_gmail_username(email)
            user = {**decoded_token, "is_admin": False, "gmail_username": gmail_username}
            authenticated_users[gmail_username] = user
            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token: {str(e)}",
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
