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

# Settings are strict: a missing required value or an unreachable Secret Manager
# raises on the first get_settings() instead of booting with a blank credential.
# Validating that in a throwaway container keeps a bad config from taking the live
# app down — --force-recreate stops the running one before the new one is proven.
echo "Preflight: resolving settings with the new image..."
$COMPOSE -f $COMPOSE_FILE --env-file .env run --rm --no-deps app \
  python -c "from app.core.settings import get_settings; get_settings(); print('settings OK')"

echo "Recreating app container..."
# The app container runs `alembic upgrade head` before uvicorn (see
# docker-compose.vm.yml), so migrations apply automatically on start.
$COMPOSE -f $COMPOSE_FILE --env-file .env up -d --force-recreate app

# curl is absent from the slim image; a failed migration kills the container outright.
echo "Waiting for the app to answer..."
for _ in $(seq 45); do
  if docker exec memoryful-app \
    python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/', timeout=3)" \
    >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 2
done

if [ -z "${healthy:-}" ]; then
  echo "App never answered; recent logs:"
  docker logs --tail=60 memoryful-app || true
  exit 1
fi
echo "App is healthy."

echo "Starting VM stack..."
$COMPOSE -f $COMPOSE_FILE --env-file .env up -d

echo "Deployment complete!"
echo "Container status:"
$COMPOSE -f $COMPOSE_FILE --env-file .env ps

echo "Recent app logs:"
docker logs --tail=40 memoryful-app

echo "Recent Celery logs:"
docker logs --tail=40 celery-worker
