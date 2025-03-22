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
        await update.message.reply_text("✅ You're already verified! Send a .txt file with contact details.")
        return WAITING_FOR_FILE

    await update.message.reply_text("🔒 This bot is password-protected. Please enter the password:")
    return WAITING_FOR_PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    input_password = update.message.text.strip()

    if input_password == PASSWORD:
        authorized_users.add(user_id)
        await update.message.reply_text("✅ Password verified! Now, send me a .txt file containing contact details.")
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
        await update.message.reply_text("⚠️ Please upload a valid .txt file containing contact details.")
        return WAITING_FOR_FILE

    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    # Read the text file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error reading file: {e}")
        return ConversationHandler.END

    if not lines:
        await update.message.reply_text("⚠️ The file is empty. Please send a valid .txt file with contact details.")
        return ConversationHandler.END

    # Process the file content
    contacts = []
    for i, line in enumerate(lines, start=1):
        parts = line.split(",", 1)  # Split into name and number if possible
        if len(parts) == 2:
            name, number = parts
        else:
            name, number = f"Name{i}", parts[0]  # Auto-generate name if missing

        contacts.append((name.strip(), number.strip()))

    # Generate the VCF file
    vcf_filename = "contacts.vcf"
    with open(vcf_filename, "w", encoding="utf-8") as vcf_file:
        for name, number in contacts:
            vcf_file.write(f"BEGIN:VCARD\nFN:{name}\nTEL:{number}\nEND:VCARD\n\n")

    # Send the generated VCF file
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

📌 **How to Use:**  
1️⃣ Send a `.txt` file with contact details  
   - Format: `Name,Number` (e.g., `John Doe, +1234567890`)  
   - If only numbers are provided, names like `Name1`, `Name2` will be assigned automatically  
2️⃣ Get the converted `.vcf` file!"""
    
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