#!/bin/bash

echo "🚀 Starting trading platform monitor..."

# First time setup - ensure containers are running
echo "📦 Initial container setup..."
docker compose up -d

while true; do
    echo -e "\n🔍 Checking for updates at $(date)"
    
    # Store current git hash
    CURRENT_HASH=$(git rev-parse HEAD)
    
    # Pull changes
    git pull
    
    # Get new git hash
    NEW_HASH=$(git rev-parse HEAD)
    
    if [ "$CURRENT_HASH" != "$NEW_HASH" ]; then
        echo "🔄 Changes detected! Updating containers..."
        echo "⏬ Stopping containers..."
        docker compose down
        
        echo "🏗️  Rebuilding containers..."
        docker compose build
        
        echo "⏫ Starting containers..."
        docker compose up -d
        
        echo "✅ Update completed successfully!"
    else
        echo "👌 Already up to date"
    fi
    
    # Wait for 1 minute before next check
    sleep 60
done