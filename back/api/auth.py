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

async def get_current_user(request: Request):
    auth_header = request.headers.get('Authorization')
    print(f"Received Authorization header: {auth_header[:20] if auth_header else 'None'}")
    print(f"All headers: {request.headers}")
    
    if not auth_header:
        print("No Authorization header found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Authorization header found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if auth_header and auth_header.startswith('Basic '):
        # Admin authentication (unchanged)
        print("Attempting Basic authentication")
        credentials = HTTPBasicCredentials.parse(auth_header)
        correct_username = secrets.compare_digest(credentials.username, "admin")
        correct_password = secrets.compare_digest(credentials.password, "admin")
        if not (correct_username and correct_password):
            print("Admin authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect admin credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        print("Admin authentication successful")
        return {"username": "admin", "is_admin": True}
    
    elif auth_header and auth_header.startswith('Bearer '):
        # Firebase authentication
        print("Attempting Firebase authentication")
        firebase_auth = get_firebase_auth()
        token = auth_header.split('Bearer ')[1]
        print(f"Attempting to verify Firebase token: {token[:20]}...")
        try:
            decoded_token = firebase_auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
            
            server_time = int(time.time())
            token_iat = decoded_token.get('iat', 0)
            print(f"Token verified. Server time: {server_time}, Token iat: {token_iat}, Difference: {server_time - token_iat}")
            
            return {**decoded_token, "is_admin": False}
        except auth.RevokedIdTokenError:
            print("Token has been revoked")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
        except auth.InvalidIdTokenError:
            print("Invalid token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except auth.ExpiredIdTokenError:
            print("Token has expired")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except Exception as e:
            print(f"Firebase authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    else:
        print("Invalid authentication method")
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