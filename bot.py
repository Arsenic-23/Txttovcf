import logging
import os
import time
import threading
import requests
import vobject
import sys
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import config

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
PASSWORD = config.PASSWORD
KEEP_ALIVE_URL = config.KEEP_ALIVE_URL
authorized_users = set()
user_data = {}

WAITING_FOR_NAME = 1
WAITING_FOR_PASSWORD = 2

# --- Dummy HTTP Server for Health Check ---
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
                print("⚠️ Another instance is running. Skipping duplicate launch.")
                return
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
        time.sleep(300)  # Ping every 5 minutes

threading.Thread(target=keep_alive, daemon=True).start()

# --- Restart on Crash ---
def restart_bot():
    print("🔄 Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)

# --- Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in authorized_users:
        await update.message.reply_text("You're already authorized! Send me a file to convert.")
        return
    
    await update.message.reply_text("🔒 This bot is password-protected. Please enter the password:")
    return WAITING_FOR_PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    input_password = update.message.text.strip()

    if input_password == PASSWORD:
        authorized_users.add(user_id)
        await update.message.reply_text("✅ Password verified! You now have access.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Incorrect password. Try again with /start.")
        return ConversationHandler.END

# --- File Handling ---
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in authorized_users:
        await update.message.reply_text("❌ Unauthorized! Use /start and enter the password.")
        return

    document = update.message.document
    if not document:
        return

    # Check file type
    if not document.file_name.endswith(".vcf"):
        await update.message.reply_text("⚠️ Only .vcf files are supported.")
        return

    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    user_data[user_id] = file_path  # Store per user instead of per chat
    await update.message.reply_text("File received! Send a name for this contact.")
    return WAITING_FOR_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in authorized_users:
        await update.message.reply_text("❌ Unauthorized! Use /start and enter the password.")
        return

    contact_name = update.message.text.strip()

    if user_id not in user_data:
        await update.message.reply_text("No file uploaded. Please upload a file first.")
        return ConversationHandler.END

    file_path = user_data.pop(user_id)
    
    await update.message.reply_text(f"Converting file: {contact_name}...")

    vcf_filename = f"{contact_name}.vcf"
    with open(vcf_filename, "w", encoding="utf-8") as vcf_file:
        vcf_file.write(f"BEGIN:VCARD\nFN:{contact_name}\nEND:VCARD")

    with open(vcf_filename, "rb") as vcf_file:
        await update.message.reply_document(document=vcf_file, filename=vcf_filename, caption="Converted file.")

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
1️⃣ Send a file  
2️⃣ Enter a contact name  
3️⃣ Get the converted .vcf file!"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --- Main Bot Function ---
def main():
    try:
        app = Application.builder().token(config.BOT_TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
                WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            },
            fallbacks=[],
        )

        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

        print("🚀 Bot is running...")
        app.run_polling()

    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        restart_bot()

if __name__ == "__main__":
    main()