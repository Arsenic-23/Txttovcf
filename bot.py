import logging
import os
import time
import threading
import requests
import sys
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import config

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
WAITING_FOR_NAME = 3

# --- Dummy HTTP Server for Koyeb Health Check ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_http_server():
    try:
        server = HTTPServer(("0.0.0.0", 8080), HealthCheckHandler)
        print("✅ Dummy HTTP server running on port 8080...")
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ Error starting dummy server: {e}")

threading.Thread(target=start_dummy_http_server, daemon=True).start()

# --- Prevent Multiple Instances ---
def check_instance():
    script_name = os.path.basename(__file__)
    current_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and script_name in cmdline and proc.pid != current_pid:
                print("⚠️ Another instance is running. Exiting...")
                sys.exit()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

check_instance()

# --- Keep-Alive Function ---
def keep_alive():
    while True:
        try:
            requests.get(KEEP_ALIVE_URL, timeout=5)
            print("🔄 Keep-alive ping sent...")
        except Exception as e:
            print(f"⚠️ Keep-alive error: {e}")
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# --- Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in authorized_users:
        await update.message.reply_text("✅ You're already verified! Send a .txt file with a phone number.")
        return WAITING_FOR_FILE

    await update.message.reply_text("🔒 This bot is password-protected. Please enter the password:")
    return WAITING_FOR_PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    input_password = update.message.text.strip()

    if input_password == PASSWORD:
        authorized_users.add(user_id)
        await update.message.reply_text("✅ Password verified! Now, send me a .txt file containing a phone number.")
        return WAITING_FOR_FILE
    else:
        await update.message.reply_text("❌ Incorrect password. Try again with /start.")
        return ConversationHandler.END

# --- File Handling ---
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in authorized_users:
        await update.message.reply_text("❌ Unauthorized! Use /start and enter the password.")
        return ConversationHandler.END

    document = update.message.document
    if not document or not document.file_name.endswith(".txt"):
        await update.message.reply_text("⚠️ Please upload a valid .txt file containing a phone number.")
        return WAITING_FOR_FILE

    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    user_data[user_id] = file_path
    await update.message.reply_text("✅ File received! Now, send a name for the contact.")
    return WAITING_FOR_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in authorized_users:
        await update.message.reply_text("❌ Unauthorized! Use /start and enter the password.")
        return ConversationHandler.END

    contact_name = update.message.text.strip()

    if user_id not in user_data:
        await update.message.reply_text("⚠️ No file uploaded. Please send a .txt file first.")
        return ConversationHandler.END

    file_path = user_data.pop(user_id)

    # Read the text file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            phone_number = f.read().strip()
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error reading file: {e}")
        return ConversationHandler.END

    if not phone_number.isdigit():
        await update.message.reply_text("⚠️ The file should contain a valid phone number.")
        return ConversationHandler.END

    vcf_filename = f"{contact_name}.vcf"
    with open(vcf_filename, "w", encoding="utf-8") as vcf_file:
        vcf_file.write(f"BEGIN:VCARD\nFN:{contact_name}\nTEL:{phone_number}\nEND:VCARD")

    with open(vcf_filename, "rb") as vcf_file:
        await update.message.reply_document(document=vcf_file, filename=vcf_filename, caption="📂 Here is your converted VCF file!")

    os.remove(file_path)
    os.remove(vcf_filename)

    return ConversationHandler.END

# --- /help command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """🤖 **Bot Commands:**  
/start - Start & enter password  
/help - Show help  
/changepassword <new_password> - Change password (Owner only)  
/verify <password> - Verify password  

📌 **How to Use:**  
1️⃣ Send a `.txt` file containing a phone number  
2️⃣ Enter a contact name  
3️⃣ Get the converted `.vcf` file!"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --- Main Bot Function ---
def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
                WAITING_FOR_FILE: [MessageHandler(filters.Document.ALL, handle_file)],
                WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            },
            fallbacks=[],
        )

        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("help", help_command))

        print("🚀 Bot is running...")
        app.run_polling()

    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        restart_bot()

if __name__ == "__main__":
    main()