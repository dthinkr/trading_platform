#!/bin/bash
# Simple deployment script for refactoring-v2 branch

set -e  # Exit on any error

echo "🚀 Starting deployment..."

# Pull latest changes
echo "📥 Pulling latest changes from refactoring-v2..."
git fetch origin
git reset --hard origin/refactoring-v2

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose down

# Pull latest images (if using pre-built images from registry)
echo "📦 Pulling latest Docker images..."
docker compose pull || echo "⚠️  No remote images to pull, will use local build"

# Start containers
echo "🏃 Starting containers..."
docker compose up -d

echo "✅ Deployment complete!"
echo "🌐 Backend: http://localhost:8000"
echo "🎨 Frontend: Check docker logs for Firebase hosting URL"

# Show status
docker compose ps
