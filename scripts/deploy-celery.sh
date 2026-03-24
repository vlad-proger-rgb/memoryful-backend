#!/bin/bash
set -e

echo "Deploying Celery workers..."

cd ~/memoryful-backend

echo "Pulling latest code..."
git pull origin main

echo "Stopping current workers..."
docker-compose -f docker/docker-compose.celery.yml down

echo "Building and starting workers..."
docker-compose -f docker/docker-compose.celery.yml up -d --build

echo "Deployment complete!"
echo ""
echo "Container status:"
docker-compose -f docker/docker-compose.celery.yml ps

echo ""
echo "Recent logs:"
docker-compose -f docker/docker-compose.celery.yml logs --tail=20
