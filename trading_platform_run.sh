#!/bin/bash

# trading_platform_run.sh

set -e

# Function to read user input
read_input() {
  local prompt="$1"
  local variable="$2"
  local default="$3"
  
  echo -n "$prompt "
  read -r response
  
  if [ -z "$response" ]; then
    eval "$variable=\"$default\""
  else
    eval "$variable=\"$response\""
  fi
}

run_docker_compose() {
  if docker compose version &> /dev/null; then
    docker compose "$@"
  else
    echo "Error: Docker Compose is not available."
    echo "Please install Docker Compose and try again."
    exit 1
  fi
}

# Function to check for updates and restart
check_update_and_restart() {
  echo "Checking for updates..."
  git fetch origin
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse @{u})

  if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Update available. Pulling changes..."
    git pull origin deploy
    echo "Restarting containers with new version..."
    if run_docker_compose up --build -d; then
      echo "Update successful!"
    else
      echo "Update failed. Reverting to previous version..."
      git reset --hard HEAD@{1}
      run_docker_compose up -d
    fi
  else
    echo "No updates available."
  fi
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check Docker version
docker_version=$(docker --version | awk '{print $3}' | cut -d',' -f1)
echo "Docker version: $docker_version"

# Check if Docker Compose is available
if run_docker_compose version &> /dev/null; then
    compose_version=$(run_docker_compose version --short)
    echo "Docker Compose version: $compose_version"
else
    echo "Error: Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Clone the repository if it doesn't exist, otherwise update it
if [ ! -d "trading_platform" ]; then
  git clone https://github.com/dthinkr/trading_platform.git
  cd trading_platform || exit
else
  cd trading_platform || exit
  check_update_and_restart
fi

# Prompt for ngrok authtoken if ngrok.yml doesn't exist
if [ ! -f "ngrok.yml" ]; then
  # Prompt for ngrok authtoken
  read_input "Enter your ngrok authtoken:" ngrok_authtoken

  # Set default hostname
  default_hostname="dthinkr.ngrok.app"

  # Prompt for ngrok hostname with default option
  read_input "Enter your ngrok hostname (press Enter to use $default_hostname):" ngrok_hostname "$default_hostname"

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
fi

# Log in to Docker Hub
echo "Logging in to Docker Hub..."
if ! docker login; then
    echo "Error: Failed to log in to Docker Hub. Please check your credentials and try again."
    exit 1
fi

# Build and start the containers
echo "Building and starting containers..."
if ! run_docker_compose up --build -d; then
    echo "Error: Failed to build and start containers. Please check the Docker Compose file and try again."
    exit 1
fi

echo "Trading platform is now running!"
echo "Your ngrok hostname is: $ngrok_hostname"

# Show logs and keep the script running
echo "Showing logs. Press Ctrl+C to stop."
run_docker_compose logs -f &

# Periodically check for updates
while true; do
  sleep 300  # Check every 5 minutes
  check_update_and_restart
done