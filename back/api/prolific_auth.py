import os
from fastapi import HTTPException, status, Request
from typing import Dict, Optional, Tuple

def extract_prolific_params(request: Request) -> Optional[Dict[str, str]]:
    """
    Extract Prolific parameters from request query parameters.
    Returns a dictionary with PROLIFIC_PID, STUDY_ID, and SESSION_ID if all are present.
    """
    query_params = request.query_params
    prolific_pid = query_params.get('PROLIFIC_PID')
    study_id = query_params.get('STUDY_ID')
    session_id = query_params.get('SESSION_ID')
    
    # Check if all required parameters are present
    if prolific_pid and study_id and session_id:
        return {
            'PROLIFIC_PID': prolific_pid,
            'STUDY_ID': study_id,
            'SESSION_ID': session_id
        }
    return None

def validate_prolific_user(prolific_params: Dict[str, str]) -> Tuple[bool, Dict]:
    """
    Validate a user based on Prolific parameters.
    For now, we're just accepting any user with valid Prolific parameters without validation.
    
    Returns:
        Tuple[bool, Dict]: (is_valid, user_data)
    """
    if not prolific_params:
        return False, {}
    
    # Extract the Prolific ID to use as the username
    prolific_pid = prolific_params.get('PROLIFIC_PID')
    
    # Create a user object similar to what we'd get from Firebase
    # but with Prolific information instead
    user = {
        'uid': f"prolific_{prolific_pid}",
        'email': f"{prolific_pid}@prolific.co",  # Create a pseudo-email
        'gmail_username': prolific_pid,  # Use Prolific ID as username
        'is_admin': False,  # Prolific users are never admins
        'is_prolific': True,  # Mark as Prolific user
        'prolific_data': prolific_params  # Store original Prolific data
    }
    
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
    prolific_params = extract_prolific_params(request)
    
    if not prolific_params:
        return None
    
    # Validate the Prolific user
    is_valid, user_data = validate_prolific_user(prolific_params)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Prolific credentials",
        )
    
    return user_data
