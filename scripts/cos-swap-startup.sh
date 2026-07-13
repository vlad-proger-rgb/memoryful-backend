#!/bin/bash
# COS resets / and /etc on every boot, so swap must be re-created/re-enabled here.
# Installed as the VM's startup-script metadata (see scripts/deploy-app.sh notes).
SWAPFILE=/mnt/stateful_partition/swapfile

if [ ! -f "$SWAPFILE" ]; then
  fallocate -l 1G "$SWAPFILE"
  chmod 600 "$SWAPFILE"
  mkswap "$SWAPFILE"
fi

swapon "$SWAPFILE" 2>/dev/null || true
