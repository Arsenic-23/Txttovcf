import os

# Bot Configuration
BOT_TOKEN = "7627624375:AAGbZYwbB9ATZsQt1SeGXrAqoSAlPhY2WEQ"  # Your bot token
OWNER_ID = 7212032106  # Your Telegram User ID

# Password System
DEFAULT_PASSWORD = "SecurePass123"  # Change this for initial setup
PASSWORD = os.getenv("BOT_PASSWORD", DEFAULT_PASSWORD)  # Allows setting via environment variable
KEEP_ALIVE_URL = "https://your-koyeb-url.koyeb.app/"