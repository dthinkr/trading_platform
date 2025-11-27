#!/bin/bash

MODE=${1:-dev}

if [ "$MODE" = "dev" ]; then
    echo "🚀 starting in LOCAL DEV mode..."
    
    # stop containers
    docker compose down
    
    # start only backend with dev env
    docker compose --env-file .env.dev up -d back
    
    echo ""
    echo "✅ backend running at http://localhost:8000"
    echo "🎨 start frontend: cd front && npm run dev"
    echo "📝 view logs: docker compose logs -f back"
    
elif [ "$MODE" = "prod" ]; then
    echo "🚀 starting in PRODUCTION mode (with ngrok)..."
    
    docker compose down
    docker compose build back
    docker compose up -d back ngrok
    
    echo ""
    echo "✅ production running"
    echo "  backend: http://localhost:8000"
    echo "  public:  https://dthinkr.ngrok.app"
    echo "📝 view logs: docker compose logs -f"
    
elif [ "$MODE" = "deploy" ]; then
    set -e
    echo "🚀 deploying from refactoring-v2..."
    
    git fetch origin
    git reset --hard origin/refactoring-v2
    
    docker compose down
    docker compose pull || echo "⚠️  no remote images, using local build"
    docker compose up -d
    
    echo ""
    echo "✅ deployment complete"
    echo "  backend: http://localhost:8000"
    docker compose ps
    
else
    echo "usage: sh run.sh [dev|prod|deploy]"
    echo ""
    echo "  dev    - local development (backend only)"
    echo "  prod   - production with ngrok"
    echo "  deploy - pull latest & restart containers"
    exit 1
fi
