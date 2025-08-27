#!/usr/bin/env python3
import os
import socket
import subprocess
import logging
import time

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv, find_dotenv

# ========= Env / Token =========
ROOT = os.path.dirname(os.path.dirname(__file__))  # /mnt/.../fs42-custom
DOTENV_PATH = os.path.join(ROOT, ".env")
load_dotenv(DOTENV_PATH, override=True)
if not os.getenv("DISCORD_TOKEN"):
    load_dotenv(find_dotenv(), override=True)

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(f"DISCORD_TOKEN not set. Expected in {DOTENV_PATH}")

# ========= Config =========
SOCKET_PATH = "/tmp/mpvsocket"

START_SCRIPT   = "/mnt/media01/projects/fs42-custom/bin/start.sh"
RESTART_SCRIPT = "/mnt/media01/projects/fs42-custom/bin/restart.sh"
KILL_SCRIPT    = "/mnt/media01/projects/fs42-custom/bin/kill.sh"

LOGDIR = "/mnt/media01/projects/fs42-custom/logs"
os.makedirs(LOGDIR, exist_ok=True)

# ========= Logging =========
logging.basicConfig(
    filename=os.path.join(LOGDIR, "cable_bot.log"),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("CableBot")

# ========= Discord Setup =========
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========= Helpers =========
def send_to_mpv(command: str) -> bool:
    """Send a JSON IPC command line to mpv's UNIX socket."""
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(1.5)
        client.connect(SOCKET_PATH)
        client.send((command + "\n").encode("utf-8"))
        client.close()
        logger.info(f"Sent to MPV: {command}")
        return True
    except Exception as e:
        logger.error(f"Socket error: {e}")
        return False

def run_script(script_path: str, label: str) -> bool:
    """Fire-and-forget script launcher with logging and output capture."""
    try:
        if not os.path.exists(script_path):
            logger.error(f"{label}: script not found: {script_path}")
            return False

        # Breadcrumb
        with open(os.path.join(LOGDIR, "bot-invocations.log"), "a") as f:
            f.write(f"{time.strftime('%F %T')} {label} -> {script_path}\n")

        # Capture outputs
        out = open(os.path.join(LOGDIR, "bot-scripts.out"), "ab", buffering=0)
        err = open(os.path.join(LOGDIR, "bot-scripts.err"), "ab", buffering=0)

        # Launch via absolute bash login shell to avoid PATH/env quirks
        subprocess.Popen(
            ["/bin/bash", "-lc", script_path],
            env=os.environ.copy(),
            stdout=out,
            stderr=err,
        )
        logger.info(f"{label} script triggered: {script_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to run {label}: {e}")
        return False

# Track current channel number in memory (for /up /down)
current_channel = 1

# ========= Events =========
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} global commands")
    except Exception as e:
        logger.error(f"❌ Sync error: {e}")

# ========= Commands: player/channel =========
@bot.tree.command(name="channel", description="Change FS42 channel (e.g. /channel 101)")
async def channel(interaction: discord.Interaction, number: int):
    global current_channel
    current_channel = number
    msg = f'{{ "command": ["show-text", "Channel {number}", 3000, 1, true] }}'
    ok = send_to_mpv(msg)
    await interaction.response.send_message(
        f"📺 Switched to channel **{number}**" if ok else "❌ Failed to send channel to mpv.",
        ephemeral=True,
    )

@bot.tree.command(name="up", description="Switch channel up by 1")
async def up(interaction: discord.Interaction):
    global current_channel
    current_channel += 1
    msg = f'{{ "command": ["show-text", "Channel {current_channel}", 3000, 1, true] }}'
    ok = send_to_mpv(msg)
    await interaction.response.send_message(
        f"🔼 Channel up → **{current_channel}**" if ok else "❌ Failed to change channel.",
        ephemeral=True,
    )

@bot.tree.command(name="down", description="Switch channel down by 1")
async def down(interaction: discord.Interaction):
    global current_channel
    current_channel = max(1, current_channel - 1)
    msg = f'{{ "command": ["show-text", "Channel {current_channel}", 3000, 1, true] }}'
    ok = send_to_mpv(msg)
    await interaction.response.send_message(
        f"🔽 Channel down → **{current_channel}**" if ok else "❌ Failed to change channel.",
        ephemeral=True,
    )

@bot.tree.command(name="fs42text", description="Inject custom text into FS42 screen (MPV OSD)")
async def fs42text(interaction: discord.Interaction, message: str):
    msg = f'{{ "command": ["show-text", "{message}", 5000, 1, true] }}'
    ok = send_to_mpv(msg)
    await interaction.response.send_message(
        f"✅ Injected text: `{message}`" if ok else "❌ Failed to inject text.",
        ephemeral=True,
    )

# ========= Commands: script control =========
@bot.tree.command(name="start", description="Start FS42 services")
async def start_cmd(interaction: discord.Interaction):
    ok = run_script(START_SCRIPT, "Start")
    await interaction.response.send_message(
        "🚀 FS42 **start.sh** triggered." if ok else "❌ Failed to start FS42.",
        ephemeral=True,
    )

@bot.tree.command(name="restart", description="Restart FS42 services")
async def restart_cmd(interaction: discord.Interaction):
    ok = run_script(RESTART_SCRIPT, "Restart")
    await interaction.response.send_message(
        "🔁 FS42 **restart.sh** triggered." if ok else "❌ Failed to restart FS42.",
        ephemeral=True,
    )

@bot.tree.command(name="kill", description="Kill FS42 services")
async def kill_cmd(interaction: discord.Interaction):
    ok = run_script(KILL_SCRIPT, "Kill")
    await interaction.response.send_message(
        "🛑 FS42 **kill.sh** triggered." if ok else "❌ Failed to kill FS42.",
        ephemeral=True,
    )

# ========= Diagnostics =========
@bot.tree.command(name="status", description="Check FS42 processes")
async def status(interaction: discord.Interaction):
    try:
        result = subprocess.run(
            "pgrep -af 'mpv|field_player|ffmpeg|Xvfb|openbox'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        txt = result.stdout.strip()
        if txt:
            msg = f"📊 **FS42 running:**\n```\n{txt}\n```"
        else:
            msg = "⚠️ FS42 processes not running."
        await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        await interaction.response.send_message(f"❌ Status check failed: {e}", ephemeral=True)

@bot.tree.command(name="which", description="Show script paths & perms")
async def which(interaction: discord.Interaction):
    import stat
    def info(p):
        try:
            st = os.stat(p)
            x = "x" if (st.st_mode & stat.S_IXUSR) else "-"
            return f"{p} size={st.st_size} exec={x} mtime={time.ctime(st.st_mtime)}"
        except Exception as e:
            return f"{p} ERROR: {e}"
    lines = [info(START_SCRIPT), info(RESTART_SCRIPT), info(KILL_SCRIPT)]
    await interaction.response.send_message("```\n" + "\n".join(lines) + "\n```", ephemeral=True)

@bot.tree.command(name="ping", description="Check bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

# ========= Run =========
logger.info("Starting CableBot...")
bot.run(TOKEN)
