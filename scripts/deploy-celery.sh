#!/bin/bash
set -e

# Docker Compose command for Container-Optimized OS
COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $PWD:$PWD -w=$PWD docker/compose:1.26.2"
COMPOSE_FILE="docker/docker-compose.celery.yml"

echo "Deploying Celery workers..."

cd ~/memoryful-backend

echo "Pulling latest code..."
git pull origin main

echo "Stopping current workers..."
$COMPOSE -f $COMPOSE_FILE down

echo "Building and starting workers..."
$COMPOSE -f $COMPOSE_FILE up -d --build

echo "Deployment complete!"
echo ""
echo "Container status:"
$COMPOSE -f $COMPOSE_FILE ps

echo ""
echo "Recent logs:"
$COMPOSE -f $COMPOSE_FILE logs --tail=20
