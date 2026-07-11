#!/bin/bash
set -e

COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $PWD:$PWD -v $HOME/.docker/config.json:/root/.docker/config.json:ro -w=$PWD docker/compose:1.26.2"
COMPOSE_FILE="docker/docker-compose.vm.yml"

echo "Deploying Memoryful VM stack..."

cd ~/memoryful-backend

echo "Pulling latest code..."
git pull origin main

echo "Pulling latest app image..."
$COMPOSE -f $COMPOSE_FILE --env-file .env pull app nginx watchtower

echo "Building Celery worker image..."
$COMPOSE -f $COMPOSE_FILE --env-file .env build celery-worker

echo "Recreating app container..."
$COMPOSE -f $COMPOSE_FILE --env-file .env up -d --force-recreate app

echo "Running database migrations..."
docker exec memoryful-app alembic upgrade head

echo "Starting VM stack..."
$COMPOSE -f $COMPOSE_FILE --env-file .env up -d

echo "Deployment complete!"
echo "Container status:"
$COMPOSE -f $COMPOSE_FILE --env-file .env ps

echo "Recent app logs:"
docker logs --tail=40 memoryful-app

echo "Recent Celery logs:"
docker logs --tail=40 celery-worker
