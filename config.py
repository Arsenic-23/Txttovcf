import os

# Bot Configuration
BOT_TOKEN = "7322155012:AAFsPRbLcnYqGJWbPazo2sABM79WBDIsjY8"  # Your bot token
OWNER_ID = 7212032106  # Your Telegram User ID

# Password System
DEFAULT_PASSWORD = "SecurePass123"  # Change this for initial setup
PASSWORD = os.getenv("BOT_PASSWORD", DEFAULT_PASSWORD)  # Allows setting via environment variable
KEEP_ALIVE_URL = "https://your-koyeb-url.koyeb.app/"