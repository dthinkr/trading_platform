import requests
import json
from urllib.parse import urlencode

# Test parameters
BASE_URL = "http://localhost:8000"  # Change to your actual backend URL when testing
PROLIFIC_PID = "test_prolific_user_123"
STUDY_ID = "test_study_456"
SESSION_ID = "test_session_789"

def test_prolific_auth():
    """Test the Prolific authentication flow"""
    # Construct URL with Prolific parameters
    params = {
        "PROLIFIC_PID": PROLIFIC_PID,
        "STUDY_ID": STUDY_ID,
        "SESSION_ID": SESSION_ID
    }
    
    login_url = f"{BASE_URL}/user/login?{urlencode(params)}"
    
    # Make the request
    try:
        response = requests.post(login_url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Authentication successful!")
            print(json.dumps(data, indent=2))
            
            # Check if we got a trader_id and market_id
            if "data" in data and "trader_id" in data["data"] and "market_id" in data["data"]:
                print(f"Trader ID: {data['data']['trader_id']}")
                print(f"Market ID: {data['data']['market_id']}")
                return True
            else:
                print("Missing trader_id or market_id in response")
                return False
        else:
            print(f"Authentication failed: {response.text}")
            return False
    except Exception as e:
        print(f"Error during authentication test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Prolific authentication...")
    success = test_prolific_auth()
    print(f"Test {'succeeded' if success else 'failed'}")
