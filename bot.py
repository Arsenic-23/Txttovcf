import logging
import os
import time
import threading
import requests
import sys
import config
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Variables
PASSWORD = config.PASSWORD
BOT_TOKEN = config.BOT_TOKEN
KEEP_ALIVE_URL = config.KEEP_ALIVE_URL
authorized_users = set()
user_data = {}

WAITING_FOR_PASSWORD = 1
WAITING_FOR_FILE = 2
WAITING_FOR_VCF_NAME = 3

# Ensure bot auto-reconnects when phone is online
def keep_bot_alive():
    while True:
        try:
            response = requests.get(KEEP_ALIVE_URL)
            if response.status_code == 200:
                logger.info("Bot is active.")
        except Exception as e:
            logger.error(f"Error in keep-alive check: {e}")
        time.sleep(600)  # Ping every 10 minutes

# Function to start the bot
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    await update.message.reply_text(f"👋 Hello {user.first_name}! Welcome to the bot.\n\n🔑 Please enter the password to continue.")

# Password Verification
async def enter_password(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    password_attempt = update.message.text.strip()

    if password_attempt == PASSWORD:
        authorized_users.add(user_id)
        await update.message.reply_text("✅ Password correct! You can now use the bot.")
    else:
        await update.message.reply_text("❌ Incorrect password. Try again.")

# Function to change password (Owner Only)
async def change_password(update: Update, context: CallbackContext):
    if update.effective_user.id != config.OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to change the password.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /changepassword <new_password>")
        return

    new_password = " ".join(context.args)
    with open("password.txt", "w") as f:
        f.write(new_password)

    global PASSWORD
    PASSWORD = new_password
    await update.message.reply_text(f"✅ Password changed successfully! New Password: `{new_password}`")

# Auto-reconnect feature
def auto_restart():
    while True:
        os.system("python bot.py")
        time.sleep(10)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Registering handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("changepassword", change_password))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enter_password))

    # Start auto-reconnect in a separate thread
    threading.Thread(target=keep_bot_alive, daemon=True).start()
    threading.Thread(target=auto_restart, daemon=True).start()

    application.run_polling()

if __name__ == "__main__":
    main()