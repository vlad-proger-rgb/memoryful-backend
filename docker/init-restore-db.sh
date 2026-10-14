#!/bin/bash
# Auto-restore prod data into a FRESH local database.
#
# Postgres runs files in /docker-entrypoint-initdb.d/ only when the data volume
# is empty — i.e. on first boot or after `docker compose down -v`. So a full
# reset reloads the latest prod dump automatically.
#
# The dump comes from scripts/python/manage_backup.py (backups/ is mounted at
# /backups by docker-compose.local.yml).
set -euo pipefail

DUMP="/backups/neondb_backup_latest.dump"

if [ ! -f "$DUMP" ]; then
  echo "[init-restore] No dump at $DUMP — starting with an empty database."
  echo "[init-restore] Create one with: python scripts/python/manage_backup.py backup --url ..."
  exit 0
fi

echo "[init-restore] Restoring $DUMP into database '$POSTGRES_DB'..."
# --clean --if-exists makes it idempotent; benign notices are expected on a
# fresh DB, so a non-zero exit here shouldn't abort container init.
pg_restore \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-privileges \
  "$DUMP" \
  || echo "[init-restore] pg_restore reported issues (usually harmless with --clean); continuing."

echo "[init-restore] Done."
