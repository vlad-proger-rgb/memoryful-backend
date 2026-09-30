#!/bin/sh
# One worker per queue. Runs under `watchfiles`, which signals only this shell, so pass it on.
pids=""
for queue in ai apps email notifications system; do
  celery -A app.core.celery_app worker -Q "${queue}_queue" --loglevel=info --hostname="celery@${queue}_worker" &
  pids="$pids $!"
done
trap 'kill -TERM $pids 2>/dev/null; wait' INT TERM
wait
