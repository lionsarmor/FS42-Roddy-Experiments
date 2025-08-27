#!/usr/bin/env python3
import argparse
import logging
import os
import signal
import subprocess
import sys
import time

from fs42.station_manager import StationManager
from fs42.station_player import StationPlayer
from fs42.input_check import InputCheck

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger("FieldPlayer")


def main():
    parser = argparse.ArgumentParser(description="FieldStation42 Player")
    parser.add_argument("--station", type=str, default=None,
                        help="Name of the station to start on")
    parser.add_argument("--no-mpv", action="store_true",
                        help="Bypass MPV backend and stream with FFmpeg directly")
    parser.add_argument("--ffmpeg-input", type=str, default="catalog/test.mp4",
                        help="Input file/stream for FFmpeg override mode")
    parser.add_argument("--ffmpeg-output", type=str, default="rtmp://localhost:1935/mystream",
                        help="RTMP output for FFmpeg override mode")
    args = parser.parse_args()

    manager = StationManager()
    input_check = InputCheck()

    if args.station:
        try:
            channel_index = manager.stations.index(args.station)
        except ValueError:
            logger.error(f"Station {args.station} not found in manager.")
            sys.exit(1)
    else:
        channel_index = 0

    # --- Override path ---
    if args.no_mpv:
        logger.info("Running in FFmpeg override mode (skipping MPV).")

        ffmpeg_cmd = [
            "ffmpeg", "-re", "-i", args.ffmpeg_input,
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "128k",
            "-f", "flv", args.ffmpeg_output
        ]

        logger.info("Launching FFmpeg: " + " ".join(ffmpeg_cmd))
        proc = subprocess.Popen(ffmpeg_cmd)

        try:
            proc.wait()
        except KeyboardInterrupt:
            logger.info("Received SIGINT, terminating FFmpeg...")
            proc.terminate()
        return

    # --- Default MPV path ---
    player = StationPlayer(manager.stations[channel_index], input_check)

    def shutdown_handler(signum, frame):
        logger.info("Signal received, shutting down...")
        player.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        player.play()
    except Exception as e:
        logger.error(f"Fatal error in FieldPlayer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
