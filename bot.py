import logging
import os
import time
import threading
import requests
import sys
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, Contact
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import config

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Variables
PASSWORD = config.PASSWORD
BOT_TOKEN = config.BOT_TOKEN
KEEP_ALIVE_URL = config.KEEP_ALIVE_URL
OWNER_ID = config.OWNER_ID
authorized_users = set()
contact_counter = 1  # Keeps track of numbered contacts
user_data = {}

WAITING_FOR_PASSWORD = 1
WAITING_FOR_FILE = 2
WAITING_FOR_VCF_NAME = 3

# --- Contact Handling ---
async def handle_contact(update: Update, context: CallbackContext):
    global contact_counter
    contact = update.message.contact
    
    # Check if the contact already has a name
    contact_name = contact.first_name if contact.first_name else None

    if not contact_name:
        await update.message.reply_text("This contact has no name. Please enter a name:")
        user_data[update.message.chat_id] = {"contact": contact, "step": WAITING_FOR_VCF_NAME}
        return

    # Save the contact
    contact_filename = f"{contact_name}{contact_counter}.vcf"
    contact_counter += 1

    vcf_content = f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name}\nTEL:{contact.phone_number}\nEND:VCARD"
    
    with open(contact_filename, "w") as vcf_file:
        vcf_file.write(vcf_content)

    await update.message.reply_text(f"Saved contact as {contact_filename}")

# --- Handle User Response for Missing Contact Name ---
async def handle_text(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    if chat_id in user_data and user_data[chat_id].get("step") == WAITING_FOR_VCF_NAME:
        contact = user_data[chat_id]["contact"]
        contact_name = update.message.text.strip()
        
        # Save the contact
        contact_filename = f"{contact_name}{contact_counter}.vcf"
        contact_counter += 1

        vcf_content = f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name}\nTEL:{contact.phone_number}\nEND:VCARD"
        
        with open(contact_filename, "w") as vcf_file:
            vcf_file.write(vcf_content)

        await update.message.reply_text(f"Saved contact as {contact_filename}")

        del user_data[chat_id]  # Remove from tracking

# --- Password System ---
async def change_password(update: Update, context: CallbackContext):
    if update.message.chat_id != OWNER_ID:
        await update.message.reply_text("You are not authorized to change the password.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /changepassword <new_password>")
        return

    new_password = context.args[0]
    global PASSWORD
    PASSWORD = new_password

    await update.message.reply_text("✅ Password has been successfully changed!")

# --- Auto Restart on Internet Connection ---
def ensure_online():
    while True:
        try:
            response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
            if response.status_code == 200:
                print("✅ Bot is online!")
            else:
                print("⚠️ Bot is offline. Restarting...")
                os.system("python bot.py &")
        except:
            print("⚠️ No internet. Retrying...")
        time.sleep(30)

# --- Start Command ---
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Send a contact to save it.")

# --- Setup Bot ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("changepassword", change_password, pass_args=True))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    threading.Thread(target=ensure_online, daemon=True).start()
    
    application.run_polling()

if __name__ == "__main__":
    main()