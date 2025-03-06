import os
import re
from pathlib import Path

def update_env_variable(key, value):
    """
    Update an environment variable in the .env file.
    If the variable exists, it will be updated.
    If it doesn't exist, it will be added to the end of the file.
    
    Args:
        key (str): The environment variable key
        value (str): The value to set for the environment variable
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the project root directory (assuming this file is in /back/utils)
        root_dir = Path(__file__).resolve().parent.parent.parent
        env_file_path = root_dir / '.env'
        
        # Read the current .env file
        if not env_file_path.exists():
            print(f"Error: .env file not found at {env_file_path}")
            return False
            
        with open(env_file_path, 'r') as file:
            lines = file.readlines()
        
        # Check if the variable already exists
        pattern = re.compile(f'^{re.escape(key)}=.*$')
        variable_exists = False
        
        # Update the variable if it exists
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                lines[i] = f"{key}={value}\n"
                variable_exists = True
                break
        
        # Add the variable if it doesn't exist
        if not variable_exists:
            lines.append(f"\n{key}={value}\n")
        
        # Write the updated content back to the .env file
        with open(env_file_path, 'w') as file:
            file.writelines(lines)
        
        # Also update the environment variable in the current process
        os.environ[key] = value
        
        return True
    except Exception as e:
        print(f"Error updating environment variable: {e}")
        return False
