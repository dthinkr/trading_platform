import os
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin SDK using the service account file
cred = credentials.Certificate('/app/firebase-service-account.json')
firebase_admin.initialize_app(cred)

security = HTTPBearer()

@lru_cache()
def get_firebase_auth():
    return auth

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    firebase_auth = get_firebase_auth()
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get('admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user