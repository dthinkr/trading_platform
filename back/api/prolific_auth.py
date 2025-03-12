import os
import time
from fastapi import HTTPException, status, Request
from typing import Dict, Optional, Tuple

# Global storage for Prolific tokens to maintain authentication across requests
prolific_tokens = {}
# Global mapping of trader_ids to prolific users
prolific_trader_map = {}

async def extract_prolific_params(request: Request) -> Optional[Dict[str, str]]:
    """
    Extract Prolific parameters from request query parameters or headers.
    Returns a dictionary with PROLIFIC_PID, STUDY_ID, and SESSION_ID if all are present.
    """
    # First check query parameters
    query_params = request.query_params
    prolific_pid = query_params.get('PROLIFIC_PID')
    study_id = query_params.get('STUDY_ID')
    session_id = query_params.get('SESSION_ID')
    
    # Check if all required parameters are present in query params
    if prolific_pid and study_id and session_id:
        return {
            'PROLIFIC_PID': prolific_pid,
            'STUDY_ID': study_id,
            'SESSION_ID': session_id
        }
    
    # If not in query params, check headers (for subsequent requests)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Prolific '):
        token = auth_header.split('Prolific ')[1]
        if token in prolific_tokens:
            return prolific_tokens[token]['prolific_data']
    
    # Finally, check if this is a request for a specific trader
    path = request.url.path
    trader_id = None
    
    # Extract trader_id from path
    if path.startswith("/trader/"):
        # Format: /trader/HUMAN_username/...
        parts = path.split("/")
        if len(parts) > 2:
            trader_id = parts[2]  # Get the HUMAN_username part
    elif path.startswith("/trader_info/"):
        # Format: /trader_info/HUMAN_username
        trader_id = path.split("/")[-1]
    
    # For /trading/start endpoint, check if we can extract trader_id from the body
    if path.startswith("/trading/start") or path.startswith("/trading/initiate"):
        # First check if we have any trader_id in the request body
        try:
            body = await request.json()
            if 'trader_id' in body:
                trader_id = body['trader_id']
        except:
            # If we can't parse the body, just continue with other methods
            pass
            
        # If we still don't have a trader_id, try to use the first available Prolific user
        if not trader_id and prolific_trader_map:
            # Use the first available trader_id
            trader_id = next(iter(prolific_trader_map.keys()))
    
    if trader_id and trader_id in prolific_trader_map:
        return prolific_trader_map[trader_id]['prolific_data']
        
    return None

# Load credentials from .env file
def load_credentials() -> Dict[str, str]:
    """
    Load credentials from .env file.
    Returns a dictionary mapping usernames to passwords.
    """
    credentials = {}
    try:
        from pathlib import Path
        env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / ".env"
        
        if env_path.exists():
            env_content = env_path.read_text()
            for line in env_content.splitlines():
                if line.startswith("PROLIFIC_CREDENTIALS="):
                    creds_str = line.split("=", 1)[1]
                    for cred_line in creds_str.split("\n"):
                        if not cred_line.strip():
                            continue
                        parts = cred_line.strip().split(",")
                        if len(parts) == 2:
                            username, password = parts
                            credentials[username.strip()] = password.strip()
    except Exception as e:
        print(f"Error loading credentials: {str(e)}")
    
    return credentials

def validate_prolific_user(prolific_params: Dict[str, str], username: str = None, password: str = None) -> Tuple[bool, Dict]:
    """
    Validate a user based on Prolific parameters and credentials.
    
    Args:
        prolific_params: Dictionary containing Prolific parameters
        username: Optional username for credential validation
        password: Optional password for credential validation
        
    Returns:
        Tuple[bool, Dict]: (is_valid, user_data)
    """
    if not prolific_params:
        return False, {}
    
    # Extract the Prolific ID to use as the username
    prolific_pid = prolific_params.get('PROLIFIC_PID')
    
    # STRICT REQUIREMENT: Username and password must be provided
    if username is None or password is None:
        print(f"No credentials provided for Prolific user {prolific_pid}")
        return False, {}
    
    # Load credentials from settings
    credentials = load_credentials()
    
    # If no credentials are configured, fall back to default
    if not credentials:
        if username != 'user1' or password != 'password1':
            print(f"Invalid credentials for Prolific user {prolific_pid} (using default)")
            return False, {}
    else:
        # Check if username exists and password matches
        if username not in credentials or credentials[username] != password:
            print(f"Invalid credentials for Prolific user {prolific_pid}")
            return False, {}
    
    print(f"Credentials validated for Prolific user {prolific_pid}")
    
    # Generate a simple token for this session
    token = f"prolific_{prolific_pid}_{int(time.time())}"
    
    # Create a user object similar to what we'd get from Firebase
    # but with Prolific information instead
    user = {
        'uid': f"prolific_{prolific_pid}",
        'email': f"{prolific_pid}@prolific.co",  # Create a pseudo-email
        'gmail_username': prolific_pid,  # Use Prolific ID as username
        'is_admin': False,  # Prolific users are never admins
        'is_prolific': True,  # Mark as Prolific user
        'prolific_data': prolific_params,  # Store original Prolific data
        'prolific_token': token,  # Store the token for future authentication
        'credential_username': username  # Store the credential username if provided
    }
    
    # Store the token for future authentication
    prolific_tokens[token] = user
    
    # Map the trader_id to this prolific user for future lookups
    trader_id = f"HUMAN_{prolific_pid}"
    prolific_trader_map[trader_id] = user
    
    print(f"Created Prolific token for user {prolific_pid}, trader_id: {trader_id}")
    return True, user

def get_headers(prolific_params: Dict[str, str]) -> Dict[str, str]:
    """
    Generate headers for Prolific API requests.
    Currently not used for actual API calls, but could be extended in the future.
    """
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

async def authenticate_prolific_user(request: Request) -> Optional[Dict]:
    """
    Authenticate a user based on Prolific parameters in the request.
    
    Returns:
        Optional[Dict]: User data if authentication is successful, None otherwise
    """
    # Extract Prolific parameters from the request
    prolific_params = await extract_prolific_params(request)
    
    if not prolific_params:
        return None
    
    # Check for username and password in request body
    username = None
    password = None
    
    try:
        # Try to parse request body for credentials
        body = await request.json()
        username = body.get('username')
        password = body.get('password')
    except:
        # If we can't parse the body, continue without credentials
        pass
    
    # Validate the Prolific user with credentials if provided
    is_valid, user_data = validate_prolific_user(prolific_params, username, password)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Set the Authorization header for future requests
    if 'prolific_token' in user_data:
        # This would be used in a real application to set cookies or headers
        # For our purposes, we'll use the global storage
        print(f"Authenticated Prolific user: {user_data['gmail_username']}")
    
    return user_data

def get_prolific_user_by_trader_id(trader_id: str) -> Optional[Dict]:
    """
    Get a Prolific user by their trader ID.
    
    Args:
        trader_id: The trader ID in format HUMAN_username
        
    Returns:
        Optional[Dict]: User data if found, None otherwise
    """
    return prolific_trader_map.get(trader_id)
