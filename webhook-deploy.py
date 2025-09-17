#!/usr/bin/env python3
"""
Simple webhook server for auto-deployment
Run with: python3 webhook-deploy.py
"""

import json
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import hmac
import hashlib
import os

# Configuration
PORT = 9000
SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')
REPO_PATH = '/root/trading_platform'
TARGET_BRANCH = 'refactoring-v2'

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Verify GitHub signature (optional but recommended)
        signature = self.headers.get('X-Hub-Signature-256')
        if signature:
            expected_signature = 'sha256=' + hmac.new(
                SECRET.encode(), post_data, hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'Invalid signature')
                return
        
        try:
            payload = json.loads(post_data)
            
            # Check if push is to target branch
            if (payload.get('ref') == f'refs/heads/{TARGET_BRANCH}' and 
                payload.get('repository', {}).get('name') == 'trading_platform'):
                
                print(f"🚀 Received push to {TARGET_BRANCH}, deploying...")
                self.deploy()
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Deployment triggered')
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Not target branch, ignoring')
                
        except Exception as e:
            print(f"❌ Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Error: {str(e)}'.encode())
    
    def deploy(self):
        """Execute deployment commands"""
        commands = [
            f'cd {REPO_PATH}',
            f'git fetch origin',
            f'git reset --hard origin/{TARGET_BRANCH}',
            'docker compose down',
            'docker compose pull || echo "No remote images"',
            'docker compose up -d'
        ]
        
        try:
            # Execute deployment
            result = subprocess.run(
                ' && '.join(commands), 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd=REPO_PATH
            )
            
            if result.returncode == 0:
                print("✅ Deployment successful!")
                print(result.stdout)
            else:
                print("❌ Deployment failed!")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")

if __name__ == '__main__':
    server = HTTPServer(('', PORT), WebhookHandler)
    print(f"🎣 Webhook server listening on port {PORT}")
    print(f"📍 Endpoint: http://your-server:9000/webhook")
    print(f"🎯 Target branch: {TARGET_BRANCH}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down webhook server...")
        server.shutdown()
