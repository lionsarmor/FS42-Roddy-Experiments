#!/bin/bash
# fs42restart.sh — Restart FieldStation42 headless session (custom)

set -e

CUSTOM="/mnt/media01/projects/fs42-custom"
BIN="$CUSTOM/bin"

echo "[FS42] Restarting headless session..."

# Stop first
"$BIN/fs42stop.sh"

# Small pause to ensure cleanup
sleep 2

# Start fresh
"$BIN/hot_start.sh"

echo "[FS42] Restart complete."

