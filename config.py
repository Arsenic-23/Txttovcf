import os

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")  # Replace with your bot token
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))  # Replace with your Telegram User ID

# Password System
DEFAULT_PASSWORD = "SecurePass123"  # Change this for initial setup
PASSWORD = os.getenv("BOT_PASSWORD", DEFAULT_PASSWORD)  # Allows setting via environment variable