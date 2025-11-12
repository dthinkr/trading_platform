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
    
    # stop containers
    docker compose down
    
    # build and start backend + ngrok with prod env
    docker compose build back
    docker compose up -d back ngrok
    
    echo ""
    echo "✅ production running"
    echo "  backend: http://localhost:8000"
    echo "  public:  https://dthinkr.ngrok.app"
    echo "📝 view logs: docker compose logs -f"
    
else
    echo "usage: sh run.sh [dev|prod]"
    echo ""
    echo "  dev  - local development (backend only)"
    echo "  prod - production with ngrok"
    exit 1
fi
