#!/bin/bash
set -euo pipefail

# === Paths ===
FSROOT="/mnt/media01/projects/FS42-Tsar-Tools/FieldStation42"
LOGS="/mnt/media01/projects/FS42-Tsar-Tools/fs42-custom/logs"
CONFIG_DIR="/mnt/media01/projects/FS42-Tsar-Tools/fs42-custom"
MEDIAMTX_CONFIG="/etc/mediamtx/mediamtx.yml"

mkdir -p "$LOGS" "$CONFIG_DIR"

# === Runtime env ===
export DISPLAY=:99
export XDG_RUNTIME_DIR="/tmp/xdg-runtime-$(id -u)"
mkdir -p "$XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR/pulse"
chmod 700 "$XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR/pulse"

echo "=== ALSA LOOPBACK SETUP FOR FIELD PLAYER ==="

# === Cleanup old processes ===
echo "[CLEANUP] stopping old processes…"
pkill -f "Xvfb.*:99"            2>/dev/null || true
pkill -f "python.*field_player" 2>/dev/null || true
pkill -f "python.*fs42/osd"     2>/dev/null || true
pkill -f mpv                    2>/dev/null || true
pkill -f ffmpeg                 2>/dev/null || true
pkill -f pulseaudio             2>/dev/null || true
pkill -f mediamtx               2>/dev/null || true
rm -f /tmp/.X99-lock /tmp/mpvsocket /tmp/test.wav || true
sleep 2

# === Create MediaMTX config if it doesn't exist ===
if [ ! -f "$MEDIAMTX_CONFIG" ]; then
    echo "[CONFIG] Creating MediaMTX configuration at $MEDIAMTX_CONFIG..."
    sudo mkdir -p /etc/mediamtx
    sudo tee "$MEDIAMTX_CONFIG" > /dev/null << 'EOF'
# MediaMTX configuration for FS42 streaming
logLevel: info
logDestinations: [stdout, file]
logFile: /mnt/media01/projects/FS42-Tsar-Tools/fs42-custom/logs/mediamtx.log

# API for monitoring
api: yes
apiAddress: 0.0.0.0:9997

# WebRTC settings
webrtcAddress: :8889
webrtcEncryption: no
webrtcAllowOrigin: "*"
webrtcLocalUDPAddress: :8189

# RTSP settings  
rtspAddress: :8554
protocols: [tcp, udp]

# Path configuration
paths:
  mystream:
    source: publisher
    sourceProtocol: rtsp
    sourceAnyPortEnable: yes
EOF
fi

# === ALSA Loopback ===
echo "[ALSA] loading snd-aloop…"
/sbin/modprobe snd-aloop 2>/dev/null || echo "[ALSA] already loaded?"

ALSA_PLAYBACK="hw:Loopback,0,0"   # MPV plays here
ALSA_CAPTURE="hw:Loopback,1,0"    # FFmpeg records here

echo "[ALSA] testing loopback…"
(timeout 2s aplay -D "$ALSA_PLAYBACK" -f S16_LE -r 44100 -c 2 /dev/urandom >/dev/null 2>&1 || true) &
sleep 0.5
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

# === Start MediaMTX ===
echo "[MEDIAMTX] starting MediaMTX server with system config…"
nohup mediamtx "$MEDIAMTX_CONFIG" >>"$LOGS/mediamtx.log" 2>&1 &
sleep 3

# === FFmpeg capture → MediaMTX RTSP ===
echo "[FFMPEG] starting desktop capture → MediaMTX…"
nohup ffmpeg \
  -fflags nobuffer -flags low_delay -use_wallclock_as_timestamps 1 \
  -f x11grab -video_size 1920x1080 -framerate 30 -i :99.0+0,0 \
  -f alsa -thread_queue_size 8192 -i hw:Loopback,1,0 \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -pix_fmt yuv420p -g 30 -keyint_min 30 -sc_threshold 0 \
  -b:v 2000k -maxrate 2000k -bufsize 1000k \
  -c:a libopus -b:a 128k -ar 48000 -ac 2 \
  -application lowdelay -frame_duration 20 \
  -af aresample=async=1:first_pts=0 \
  -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/mystream \
  >>"$LOGS/ffmpeg.log" 2>&1 &

sleep 3

# === Start FieldStation42 ===
cd "$FSROOT"
echo "[FS42] starting field_player…"
nohup python3 field_player.py >>"$LOGS/fieldplayer.log" 2>&1 &

# === OSD watcher ===
echo "[OSD] waiting for mpv socket…"
/usr/bin/timeout 15 bash -c 'until [ -S /tmp/mpvsocket ]; do sleep 0.5; done' || {
  echo "[OSD] mpv socket not found after 15s; continuing"
}

echo "[OSD] starting watcher: fs42/osd/main.py"
nohup python3 "$FSROOT/fs42/osd/main.py" \
  >> "$LOGS/osd-forwarder.log" 2>&1 &

# === MPV Watchdog ===
echo "[WATCHDOG] starting mpv freeze monitor…"
nohup bash -c '
  LAST_POS=0
  while true; do
    sleep 10
    CUR_POS=$(echo "{ \"command\": [\"get_property\", \"time-pos\"] }" | socat - /tmp/mpvsocket 2>/dev/null | jq -r .data 2>/dev/null || echo "err")
    if [[ "$CUR_POS" == "null" || "$CUR_POS" == "err" ]]; then
      echo "[WATCHDOG] mpv not responding, restarting…" >>"'"$LOGS"'/watchdog.log"
      pkill -f "python.*field_player"
      sleep 2
      cd "'"$FSROOT"'" && nohup python3 field_player.py >>"'"$LOGS"'/fieldplayer.log" 2>&1 &
    elif [[ "$CUR_POS" == "$LAST_POS" ]]; then
      echo "[WATCHDOG] time-pos stuck at $CUR_POS, restarting mpv…" >>"'"$LOGS"'/watchdog.log"
      pkill -f "python.*field_player"
      sleep 2
      cd "'"$FSROOT"'" && nohup python3 field_player.py >>"'"$LOGS"'/fieldplayer.log" 2>&1 &
    fi
    LAST_POS=$CUR_POS
  done
' >/dev/null 2>&1 &

sleep 2

echo "=== HOT START COMPLETE ==="
echo ""
echo "🎥 MediaMTX WebRTC Player: http://100.93.192.114:8889/mystream"
echo "📊 MediaMTX API Status: http://100.93.192.114:9997"
echo "📁 Logs directory: $LOGS"
echo ""
echo "Use MediaMTX built-in player - no custom HTML needed!"
