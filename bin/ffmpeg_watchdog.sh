#!/bin/bash
LOGS="/mnt/media01/projects/FS42-Tsar-Tools/fs42-custom/logs"
ALSA_CAPTURE="hw:Loopback,1,0"

while true; do
  echo "[FFMPEG] starting at $(date)" >>"$LOGS/ffmpeg-watchdog.log"

  ffmpeg \
    -fflags nobuffer \
    -flags low_delay \
    -use_wallclock_as_timestamps 1 \
    -thread_queue_size 8192 -f x11grab -draw_mouse 0 -probesize 10M -framerate 30 -i :99 \
    -thread_queue_size 8192 -f alsa -i "$ALSA_CAPTURE" \
    -c:v libx264 -preset veryfast -tune zerolatency \
    -g 30 -keyint_min 30 -sc_threshold 0 \
    -b:v 4000k -maxrate 4000k -bufsize 2000k \
    -c:a aac -b:a 128k -ar 44100 \
    -flush_packets 1 -muxdelay 0 -muxpreload 0 \
    -f flv rtmp://localhost:1935/mystream >>"$LOGS/ffmpeg.log" 2>&1 &

  FFPID=$!

  # Stall monitor
  LAST_FRAME=0
  while kill -0 $FFPID 2>/dev/null; do
    sleep 10
    CUR_FRAME=$(grep -o "frame= *[0-9]*" "$LOGS/ffmpeg.log" | tail -1 | awk '{print $2}')
    if [[ -n "$CUR_FRAME" ]]; then
      if [[ "$CUR_FRAME" -le "$LAST_FRAME" ]]; then
        echo "[WATCHDOG] ffmpeg stalled at frame $CUR_FRAME, restarting…" >>"$LOGS/ffmpeg-watchdog.log"
        kill -9 $FFPID
        break
      fi
      LAST_FRAME=$CUR_FRAME
    fi
  done

  echo "[WATCHDOG] ffmpeg exited or killed at $(date), restarting…" >>"$LOGS/ffmpeg-watchdog.log"
  sleep 2
done
