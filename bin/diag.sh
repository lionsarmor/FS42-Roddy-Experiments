#!/bin/bash

# === Paths ===
FSROOT="/mnt/media01/projects/FieldStation42"
LOGS="/mnt/media01/projects/fs42-custom/logs"
mkdir -p "$LOGS"

# === Runtime env ===
export DISPLAY=:99
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR/pulse"
chmod 700 "$XDG_RUNTIME_DIR"

# GPU driver hint (comment/uncomment if you test VAAPI later)
# export LIBVA_DRIVER_NAME=iHD       # Intel
# export LIBVA_DRIVER_NAME=radeonsi  # AMD
# export LIBVA_DRIVER_NAME=v4l2_request  # RPi/ARM

echo "=== ALSA LOOPBACK SETUP FOR FIELD PLAYER ==="

# === Cleanup old processes ===
pkill -f "Xvfb.*:99" 2>/dev/null || true
pkill -f "python.*field_player" 2>/dev/null || true
pkill -f mpv 2>/dev/null || true
pkill -f ffmpeg 2>/dev/null || true
pkill -f pulseaudio 2>/dev/null || true
rm -f /tmp/.X99-lock /tmp/mpvsocket
sleep 2

# === ALSA Loopback ===
echo "Loading ALSA loopback..."
sudo modprobe snd-aloop 2>/dev/null || echo "snd-aloop already loaded?"

ALSA_PLAYBACK="hw:Loopback,0,0"   # MPV plays here
ALSA_CAPTURE="hw:Loopback,1,0"    # FFmpeg records from here

# quick loopback test
(timeout 2s aplay -D $ALSA_PLAYBACK -f S16_LE -r 44100 -c 2 /dev/urandom >/dev/null 2>&1 &)
sleep 0.5
if timeout 1s arecord -D $ALSA_CAPTURE -f S16_LE -r 44100 -c 2 /tmp/test.wav >/dev/null 2>&1; then
    echo "Loopback test PASSED"
else
    echo "Loopback test FAILED"
fi

# === Xvfb & openbox ===
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp >>"$LOGS/xvfb.log" 2>&1 &
sleep 2

echo "Starting openbox..."
DISPLAY=:99 openbox >>"$LOGS/openbox.log" 2>&1 &
sleep 2

# === FFmpeg capture (software x264 for stability) ===
echo "Starting FFmpeg..."
ffmpeg \
  -f x11grab -video_size 1920x1080 -framerate 30 -i :99 \
  -f alsa -thread_queue_size 1024 -i $ALSA_CAPTURE \
  -c:v libx264 -preset veryfast -tune zerolatency -g 60 -b:v 4000k \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv rtmp://localhost:1935/mystream \
  >> "$LOGS/ffmpeg.log" 2>&1 &

sleep 3

# === Start FieldStation42 ===
cd "$FSROOT"


echo "Starting field_player..."
python3 field_player.py >> "$LOGS/fieldplayer.log" 2>&1 &
sleep 2

echo "=== HOT START COMPLETE ==="
