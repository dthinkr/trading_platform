#!/bin/bash
# Server deployment script - pulls latest image and restarts
set -e
cd /root/trading_platform

echo "[$(date)] Starting deployment..."

# Pull latest image from Docker Hub
podman pull docker.io/venvoo/trading_platform:back

# Restart containers using server-specific compose file
podman-compose -f docker-compose.server.yml down 2>/dev/null || true
podman-compose -f docker-compose.server.yml up -d

echo "[$(date)] Deployment complete"
podman ps
