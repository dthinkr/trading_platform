#!/bin/bash

# trading_platform_run.sh

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Clone the repository
git clone https://github.com/dthinkr/trading_platform.git
cd trading_platform

# Prompt for ngrok authtoken
read -p "Enter your ngrok authtoken: " ngrok_authtoken

# Set default hostname
default_hostname="dthinkr.ngrok.app"

# Prompt for ngrok hostname with default option
read -p "Enter your ngrok hostname (press Enter to use $default_hostname): " ngrok_hostname
ngrok_hostname=${ngrok_hostname:-$default_hostname}

# Create ngrok.yml file
cat > ngrok.yml << EOL
version: 2
authtoken: $ngrok_authtoken
tunnels:
  combined:
    addr: nginx:80
    proto: http
    hostname: $ngrok_hostname
EOL

# Log in to Docker Hub
docker login

# Build and start the containers
docker-compose up --build -d

echo "Trading platform is now running!"
echo "Your ngrok hostname is: $ngrok_hostname"