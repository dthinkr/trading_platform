#!/usr/bin/env python3
"""
Test script for Prolific login functionality.
This script generates a test URL with a mock Prolific participant ID
that can be used to test the login flow.
"""

import argparse
import random
import string
import webbrowser
from urllib.parse import urlencode

def generate_mock_prolific_id(length=24):
    """Generate a random string to use as a mock Prolific ID."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def main():
    parser = argparse.ArgumentParser(description='Test Prolific login functionality')
    parser.add_argument('--base-url', default='http://localhost:3000', 
                        help='Base URL of the trading platform (default: http://localhost:3000)')
    parser.add_argument('--id', default=None,
                        help='Use a specific Prolific ID (default: generate random ID)')
    parser.add_argument('--open-browser', action='store_true',
                        help='Open the URL in a browser automatically')
    
    args = parser.parse_args()
    
    # Generate or use provided Prolific ID
    prolific_id = args.id or generate_mock_prolific_id()
    
    # Create query parameters
    params = {
        'PROLIFIC_PID': prolific_id,
        'STUDY_ID': 'test_study',
        'SESSION_ID': 'test_session'
    }
    
    # Build the full URL
    url = f"{args.base_url}/?{urlencode(params)}"
    
    print("\n=== Prolific Login Test ===")
    print(f"Mock Prolific ID: {prolific_id}")
    print(f"Test URL: {url}")
    print("\nInstructions:")
    print("1. Make sure your trading platform backend and frontend are running")
    print("2. Open the URL above in your browser")
    print("3. You should be automatically logged in with the mock Prolific ID")
    print("4. If login fails, check that DEV_MODE is set to True in back/api/prolific_auth.py")
    print("\nNote: Save this Prolific ID if you want to use it consistently for testing")
    
    if args.open_browser:
        print("\nOpening URL in browser...")
        webbrowser.open(url)

if __name__ == "__main__":
    main() 