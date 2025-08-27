#!/usr/bin/env python3
import os
import socket
import subprocess
import logging
import discord
from discord.ext import commands

# --- Load DISCORD_TOKEN from .env (project root) ---
from dotenv import load_dotenv
ROOT = os.path.dirname(os.path.dirname(__file__))  # /mnt/.../fs42-custom
load_dotenv(os.path.join(ROOT, ".env"))
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set. Put it in /mnt/media01/projects/fs42-custom/.env")

# === CONFIG ===
SOCKET_PATH = "/tmp/mpvsocket"

START_SCRIPT   = "/mnt/media01/projects/fs42-custom/bin/start.sh"
RESTART_SCRIPT = "/mnt/media01/projects/fs42-custom/bin/restart.sh"
KILL_SCRIPT    = "/mnt/media01/projects/fs42-custom/bin/kill.sh"

# Track current channel number in memory
current_channel = 1

# === LOGGING ===
logging.basicConfig(
    filename="/mnt/media01/projects/fs42-custom/cable_bot.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("CableBot")

# === DISCORD SETUP ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# === SOCKET SEND FUNCTION ===
def send_to_mpv(command: str) -> bool:
    """Send JSON IPC command to mpv socket"""
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
        client.send((command + "\n").encode("utf-8"))
        client.close()
        logger.info(f"Sent to MPV: {command}")
        return True
    except Exception as e:
        logger.error(f"Socket error: {e}")
        return False

# === BOT EVENTS ===
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"❌ Sync error: {e}")

# === CHANNEL COMMANDS ===
@bot.tree.command(name="channel", description="Change FS42 channel (e.g. /channel 101)")
async def channel(interaction: discord.Interaction, number: int):
    global current_channel
    current_channel = number
    await interaction.response.defer(ephemeral=True)
    msg = f'{{ "command": ["show-text", "Channel {number}", 3000, 1, true] }}'
    if send_to_mpv(msg):
        await interaction.followup.send(f"📺 Switched to channel **{number}**", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to send channel to mpv.", ephemeral=True)

@bot.tree.command(name="up", description="Switch channel up by 1")
async def up(interaction: discord.Interaction):
    global current_channel
    current_channel += 1
    await interaction.response.defer(ephemeral=True)
    msg = f'{{ "command": ["show-text", "Channel {current_channel}", 3000, 1, true] }}'
    if send_to_mpv(msg):
        await interaction.followup.send(f"🔼 Channel up → **{current_channel}**", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to change channel.", ephemeral=True)

@bot.tree.command(name="down", description="Switch channel down by 1")
async def down(interaction: discord.Interaction):
    global current_channel
    current_channel = max(1, current_channel - 1)
    await interaction.response.defer(ephemeral=True)
    msg = f'{{ "command": ["show-text", "Channel {current_channel}", 3000, 1, true] }}'
    if send_to_mpv(msg):
        await interaction.followup.send(f"🔽 Channel down → **{current_channel}**", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to change channel.", ephemeral=True)

# === TEXT INJECTION ===
@bot.tree.command(name="fs42text", description="Inject custom text into FS42 screen (MPV OSD)")
async def fs42text(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)
    msg = f'{{ "command": ["show-text", "{message}", 5000, 1, true] }}'
    if send_to_mpv(msg):
        await interaction.followup.send(f"✅ Injected text: `{message}`", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to inject text.", ephemeral=True)

# === SCRIPT RUNNERS ===
def run_script(script_path: str, label: str):
    try:
        subprocess.Popen(
            ["bash", script_path],
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"{label} script triggered: {script_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to run {label}: {e}")
        return False

@bot.tree.command(name="start", description="Start FS42 services")
async def start(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if run_script(START_SCRIPT, "Start"):
        await interaction.followup.send("🚀 FS42 **start.sh** triggered.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to start FS42.", ephemeral=True)

@bot.tree.command(name="restart", description="Restart FS42 services")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if run_script(RESTART_SCRIPT, "Restart"):
        await interaction.followup.send("🔁 FS42 **restart.sh** triggered.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to restart FS42.", ephemeral=True)

@bot.tree.command(name="kill", description="Kill FS42 services")
async def kill(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if run_script(KILL_SCRIPT, "Kill"):
        await interaction.followup.send("🛑 FS42 **kill.sh** triggered.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to kill FS42.", ephemeral=True)

# === STATUS ===
@bot.tree.command(name="status", description="Check FS42 processes")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        result = subprocess.run(
            "pgrep -af 'mpv|field_player|ffmpeg|Xvfb'",
            shell=True, capture_output=True, text=True
        )
        if result.stdout.strip():
            logger.info(f"Status check: {result.stdout.strip()}")
            await interaction.followup.send(f"📊 **FS42 running:**\n```\n{result.stdout}\n```", ephemeral=True)
        else:
            logger.warning("FS42 processes not running.")
            await interaction.followup.send("⚠️ FS42 processes not running.", ephemeral=True)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        await interaction.followup.send(f"❌ Status check failed: {e}", ephemeral=True)

# === RUN ===
logger.info("Starting CableBot...")
bot.run(TOKEN)
