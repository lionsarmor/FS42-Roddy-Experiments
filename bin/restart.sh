#!/bin/bash
set -e

echo "=== FS42 RESTART ==="

# 1) Stop & clean
echo "Stopping existing processes..."
/mnt/media01/projects/fs42-custom/bin/cleanup.sh

sleep 2

# 2) Start Xvfb
echo "Starting Xvfb..."
nohup Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac -noreset \
  >/tmp/xvfb-screen.log 2>/tmp/xvfb-errors.log &

sleep 1

# 3) Launch minimal window manager (prevents black X cursor)
echo "Launching openbox..."
DISPLAY=:99 nohup openbox >/dev/null 2>&1 &

# 4) Start PulseAudio
echo "Starting PulseAudio..."
PULSE_RUNTIME_PATH=/run/user/$(id -u)/pulse \
  nohup pulseaudio --start >/tmp/pulseaudio.log 2>&1 &

sleep 1

# 5) Start FieldPlayer (mpv frontend)
echo "Starting FieldPlayer..."
cd /mnt/media01/projects/fs42-custom
source env/bin/activate
DISPLAY=:99 \
XDG_RUNTIME_DIR=/run/user/$(id -u) \
PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native \
nohup python3 fs42/field_player.py >/tmp/fieldplayer.log 2>&1 &

sleep 2

# 6) Start OSD overlay
echo "Starting OSD..."
DISPLAY=:99 \
nohup python3 fs42/osd.py >/tmp/osd.log 2>&1 &

sleep 1

# 7) Start Station42 main loop
echo "Starting Station42..."
DISPLAY=:99 \
nohup python3 fs42/station_42.py --server >/tmp/station42.log 2>&1 &

echo "=== FS42 Restart complete. All services should be running. ==="
