#!/bin/bash
LOGS="$HOME/logs"
mkdir -p "$LOGS"

echo "[Capture] Starting FFmpeg capture from :99 (video only)..."

ffmpeg -y \
    -f x11grab -s 1366x768 -r 30 -i :99 \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -f flv rtmp://127.0.0.1:1935/mystream \
    >>"$LOGS/ffmpeg_capture.log" 2>&1
