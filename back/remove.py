# analyze_endpoints.py
from vulture import Vulture
import ast
import os

def find_unused_endpoints():
    # Initialize Vulture
    v = Vulture(verbose=True)
    
    # Add your FastAPI files
    v.scavenge(['api/endpoints.py'])
    
    # Add your Vue files to check for usage
    frontend_dir = 'front/src'
    for root, _, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith('.vue') or file.endswith('.js'):
                v.scavenge([os.path.join(root, file)])
    
    # Print unused functions that look like endpoints
    with open('api/endpoints.py', 'r') as f:
        lines = f.readlines()
        
    for item in v.unused_funcs:
        # Get the line before the function definition
        if item.first_lineno > 1:
            decorator_line = lines[item.first_lineno - 2].strip()  # -2 because line numbers start at 1
            if any(decorator in decorator_line for decorator in ['@app.get', '@app.post', '@app.put', '@app.delete']):
                print(f"Potentially unused endpoint: {item.name}")
                print(f"  Line {item.first_lineno}: {decorator_line}")
                print(f"  Path: {decorator_line.split('(')[1].split(')')[0]}")
                print()

if __name__ == "__main__":
    find_unused_endpoints()