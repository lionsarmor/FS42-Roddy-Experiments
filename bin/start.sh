#!/bin/bash
set -euo pipefail

# === Force custom OSD ===
cp /ExternalDrive/projects/fs42-custom/bin/osd/main.py \
   /ExternalDrive/projects/FieldStation42/fs42/osd/main.py
echo "[OSD] Replaced official main.py with custom version"


# === Paths ===
FSROOT="/mnt/media01/projects/FieldStation42"
LOGS="/mnt/media01/projects/fs42-custom/logs"
mkdir -p "$LOGS"

# === Runtime env ===
export DISPLAY=:99
export XDG_RUNTIME_DIR="/tmp/xdg-runtime-$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR/pulse"
chmod 700 "$XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR/pulse"

echo "=== ALSA LOOPBACK SETUP FOR FIELD PLAYER ==="

# === Cleanup old processes ===
echo "[CLEANUP] stopping old processes…"
pkill -f "Xvfb.*:99"             2>/dev/null || true
pkill -f "python.*field_player"  2>/dev/null || true
pkill -f "python.*fs42/osd/main.py" 2>/dev/null || true
pkill -f mpv                     2>/dev/null || true
pkill -f ffmpeg                  2>/dev/null || true
pkill -f pulseaudio              2>/dev/null || true
rm -f /tmp/.X99-lock /tmp/mpvsocket /tmp/test.wav || true
sleep 1

# === ALSA Loopback ===
echo "[ALSA] loading snd-aloop (ok if already loaded)…"
sudo modprobe snd-aloop 2>/dev/null || echo "[ALSA] snd-aloop already loaded?"

ALSA_PLAYBACK="hw:Loopback,0,0"   # MPV plays here
ALSA_CAPTURE="hw:Loopback,1,0"    # FFmpeg records from here

echo "[ALSA] quick loopback test…"
(timeout 2s aplay -D "$ALSA_PLAYBACK" -f S16_LE -r 44100 -c 2 /dev/urandom >/dev/null 2>&1 || true)
sleep 0.3
if timeout 1s arecord -D "$ALSA_CAPTURE" -f S16_LE -r 44100 -c 2 /tmp/test.wav >/dev/null 2>&1; then
  echo "[ALSA] Loopback test PASSED"
else
  echo "[ALSA] Loopback test FAILED (continuing anyway)"
fi
rm -f /tmp/test.wav || true

# === Xvfb & openbox ===
echo "[X] starting Xvfb on :99…"
nohup Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac -noreset >>"$LOGS/xvfb.log" 2>&1 &
sleep 1

echo "[X] starting openbox…"
DISPLAY=:99 nohup openbox >>"$LOGS/openbox.log" 2>&1 &
sleep 1

# === FFmpeg capture (low-latency RTMP) ===
echo "[FFMPEG] starting desktop capture → RTMP…"
# shorter GOP = faster viewer re-syncs; small bufsize = less latency
nohup ffmpeg \
  -fflags nobuffer \
  -flags low_delay \
  -use_wallclock_as_timestamps 1 \
  -f x11grab -video_size 1920x1080 -framerate 30 -i :99 \
  -f alsa -thread_queue_size 1024 -i "$ALSA_CAPTURE" \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -g 30 -keyint_min 30 -sc_threshold 0 \
  -b:v 4000k -maxrate 4000k -bufsize 2000k \
  -c:a aac -b:a 128k -ar 44100 \
  -flush_packets 1 -muxdelay 0 -muxpreload 0 \
  -f flv rtmp://localhost:1935/mystream >>"$LOGS/ffmpeg.log" 2>&1 &

sleep 2

# === Start FieldStation42 ===
cd "$FSROOT"
echo "[FS42] starting field_player…"
nohup python3 field_player.py >>"$LOGS/fieldplayer.log" 2>&1 &

# === OSD watcher ===
echo "[OSD] waiting for mpv socket…"
/usr/bin/timeout 15 bash -c 'until [ -S /tmp/mpvsocket ]; do sleep 0.5; done' || {
  echo "[OSD] mpv socket not found after 15s; continuing (watcher may fail)"
}

echo "[OSD] starting watcher: fs42/osd/main.py"
nohup python3 /mnt/media01/projects/FieldStation42/fs42/osd/main.py \
  >> "$LOGS/osd-forwarder.log" 2>&1 &

echo "=== HOT START COMPLETE ==="
