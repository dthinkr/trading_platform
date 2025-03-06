import os
import requests
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from functools import lru_cache

PROLIFIC_API_KEY = os.environ.get('PROLIFIC_API')
PROLIFIC_API_BASE_URL = "https://api.prolific.co/api/v1"

# Cache for participant data to avoid unnecessary API calls
participant_cache = {}
study_cache = {}


def get_headers():
    """Get the headers for the Prolific API requests."""
    if not PROLIFIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prolific API key is not configured"
        )
    
    return {
        "Authorization": f"Token {PROLIFIC_API_KEY}",
        "Content-Type": "application/json"
    }


@lru_cache(maxsize=10)
def get_study_details(study_id: str) -> Dict[str, Any]:
    """Get the details of a study from Prolific."""
    if study_id in study_cache:
        return study_cache[study_id]
    
    try:
        response = requests.get(
            f"{PROLIFIC_API_BASE_URL}/studies/{study_id}/",
            headers=get_headers()
        )
        response.raise_for_status()
        study_data = response.json()
        study_cache[study_id] = study_data
        return study_data
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching study details from Prolific: {str(e)}"
        )


def get_study_participants(study_id: str) -> List[Dict[str, Any]]:
    """Get all participants for a specific study."""
    if study_id in participant_cache:
        return participant_cache[study_id]
    
    try:
        response = requests.get(
            f"{PROLIFIC_API_BASE_URL}/studies/{study_id}/participants/",
            headers=get_headers()
        )
        response.raise_for_status()
        participants_data = response.json()
        participant_list = participants_data.get('results', [])
        participant_cache[study_id] = participant_list
        return participant_list
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching participants from Prolific: {str(e)}"
        )


def get_default_study_id() -> Optional[str]:
    """Get the default study ID from environment variables."""
    return os.environ.get('PROLIFIC_STUDY_ID')


def is_valid_participant(participant_id: str, study_id: Optional[str] = None) -> bool:
    """Check if a participant ID is valid and belongs to any of our studies.
    
    Args:
        participant_id: The Prolific participant ID to validate
        study_id: Optional specific study ID to check
        
    Returns:
        bool: True if the participant ID is valid, False otherwise
    """
    # If no specific study ID is provided, try to get the default one
    if not study_id:
        study_id = get_default_study_id()
    
    # If we have a study ID (either provided or from environment), check that study
    if study_id:
        participants = get_study_participants(study_id)
        return any(p.get('participant_id') == participant_id for p in participants)
    
    # Check all cached studies if no specific study ID is provided
    for cached_study_id in participant_cache:
        participants = participant_cache[cached_study_id]
        if any(p.get('participant_id') == participant_id for p in participants):
            return True
    
    # If not found in cache, we need to fetch from the API
    # This would require knowing all study IDs, so we'll return False for now
    # In a real implementation, you might want to maintain a list of all study IDs
    return False


def get_participant_details(participant_id: str) -> Dict[str, Any]:
    """Get details for a specific participant."""
    try:
        response = requests.get(
            f"{PROLIFIC_API_BASE_URL}/participants/{participant_id}/",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching participant details from Prolific: {str(e)}"
        )


def clear_caches():
    """Clear all caches. Useful when refreshing data."""
    participant_cache.clear()
    study_cache.clear()
    get_study_details.cache_clear()
