#!/bin/bash
set -e

# NOTE: `git pull` deliberately lives in the workflow, before this script is
# NOTE: invoked. Pulling from inside the script rewrites the script while bash is
# NOTE: still reading it, which shifts byte offsets and makes bash execute stale
# NOTE: lines from the previous version.

cd ~/memoryful-backend

COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $PWD:$PWD -v $HOME/.docker/config.json:/root/.docker/config.json:ro -w=$PWD docker/compose:1.26.2"
COMPOSE_FILE="docker/docker-compose.vm.yml"

echo "Deploying Memoryful VM stack..."

# Config ships with the code. .env.prod is the source of truth for non-secret
# settings; real secrets come from GCP Secret Manager at runtime, so nothing
# machine-specific is lost by overwriting .env here.
echo "Syncing .env from .env.prod..."
cp .env.prod .env

# App and celery images are built and pushed by CI — building the celery image
# here used to starve the VM and degrade the live site for ~10 minutes.
echo "Pulling latest images..."
$COMPOSE -f $COMPOSE_FILE --env-file .env pull app celery-worker nginx watchtower

echo "Building certbot-renew image..."
$COMPOSE -f $COMPOSE_FILE --env-file .env build certbot-renew

echo "Recreating app container..."
# The app container runs `alembic upgrade head` before uvicorn (see
# docker-compose.vm.yml), so migrations apply automatically on start.
$COMPOSE -f $COMPOSE_FILE --env-file .env up -d --force-recreate app

echo "Starting VM stack..."
$COMPOSE -f $COMPOSE_FILE --env-file .env up -d

echo "Deployment complete!"
echo "Container status:"
$COMPOSE -f $COMPOSE_FILE --env-file .env ps

echo "Recent app logs:"
docker logs --tail=40 memoryful-app

echo "Recent Celery logs:"
docker logs --tail=40 celery-worker
