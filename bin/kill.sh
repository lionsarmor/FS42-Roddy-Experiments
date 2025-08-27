#!/bin/bash
echo "=== FS42 CLEANUP ==="

# --- Kill processes safely ---
echo "Killing processes..."
pkill -f "Xvfb.*:99"            2>/dev/null || true
pkill -f "ffmpeg"               2>/dev/null || true
pkill -f "python.*field_player" 2>/dev/null || true
pkill -f "python.*station_42"   2>/dev/null || true
pkill -f "python.*channel"      2>/dev/null || true
pkill -f "python.*osd"          2>/dev/null || true
pkill -f "chromium"             2>/dev/null || true
pkill -f "chromium-browser"     2>/dev/null || true
pkill -f "mpv"                  2>/dev/null || true
pkill -f "pulseaudio"           2>/dev/null || true

# --- Remove stale sockets and lock files ---
echo "Cleaning up temp files..."
rm -f /tmp/.X99-lock
rm -f /tmp/.X11-unix/X99
rm -f /tmp/mpvsocket
rm -f /tmp/xvfb-screen.log
rm -f /tmp/xvfb-errors.log

# --- Clean up PulseAudio runtime files ---
if [ -d "/run/user/$(id -u)/pulse" ]; then
    echo "Removing PulseAudio runtime files..."
    rm -rf /run/user/$(id -u)/pulse/*
fi

# --- Reset DISPLAY runtime dir ---
if [ -d "/run/user/$(id -u)" ]; then
    chmod 700 /run/user/$(id -u) 2>/dev/null || true
fi

echo "Cleanup complete. System is ready for fresh launch."
