import logging
import os
import vobject
import sys
import psutil
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import config

# Dummy HTTP Server for Koyeb Health Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_http_server():
    try:
        server = HTTPServer(("0.0.0.0", 8080), HealthCheckHandler)
        print("Dummy HTTP server running on port 8080...")
        server.serve_forever()
    except Exception as e:
        print(f"Error starting dummy server: {e}")

# Run HTTP server in a separate thread
threading.Thread(target=start_dummy_http_server, daemon=True).start()

# Prevent multiple instances
def check_instance():
    script_name = os.path.basename(__file__)
    current_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and script_name in cmdline and proc.pid != current_pid:
                print("Another instance is running. Exiting...")
                sys.exit()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

check_instance()

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global password variable
PASSWORD = config.PASSWORD

# Dictionary to store user file data temporarily
user_data = {}

# Conversation handler states
WAITING_FOR_NAME = 1

# Verify password
def verify_password(password: str) -> bool:
    return password == PASSWORD

# Convert file to VCF
def convert_to_vcf(file_path: str, contact_name: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            contact = vobject.readOne(f)
    except Exception:
        contact = vobject.vCard()
    
    contact.add("fn").value = contact_name
    vcf_filename = f"{contact_name}.vcf"

    with open(vcf_filename, "w", encoding="utf-8") as vcf_file:
        vcf_file.write(contact.serialize())
    
    return vcf_filename

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a file, and I'll convert it into a vCard (.vcf) file. You can also provide a custom name for the contact.")

# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        return

    if document.mime_type and "vcard" in document.mime_type.lower():
        await update.message.reply_text("This file is already a VCF!")
        return

    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    # Store the file path temporarily
    user_data[update.message.chat_id] = file_path

    await update.message.reply_text("File received! Please send me a name for this contact.")
    return WAITING_FOR_NAME

# Handle custom name input
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_name = update.message.text.strip()
    chat_id = update.message.chat_id

    if chat_id not in user_data:
        await update.message.reply_text("No file was uploaded. Please upload a file first.")
        return ConversationHandler.END

    file_path = user_data.pop(chat_id)
    
    await update.message.reply_text(f"Converting file with name: {contact_name}...")

    vcf_filename = convert_to_vcf(file_path, contact_name)

    with open(vcf_filename, "rb") as vcf_file:
        await update.message.reply_document(document=vcf_file, filename=vcf_filename, caption=f"Converted file: {vcf_filename}")

    os.remove(file_path)
    os.remove(vcf_filename)

    return ConversationHandler.END

# /changepassword command
async def change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != config.OWNER_ID:
        await update.message.reply_text("You are not authorized to change the password.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /changepassword <new_password>")
        return

    global PASSWORD
    PASSWORD = context.args[0]
    await update.message.reply_text("Password changed successfully!")

# /verify command
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        input_pass = context.args[0]
        if verify_password(input_pass):
            await update.message.reply_text("Password verified successfully!")
        else:
            await update.message.reply_text("Incorrect password.")
    else:
        await update.message.reply_text("Usage: /verify <password>")

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Document.ALL, handle_file)],
        states={
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("changepassword", change_password))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(conv_handler)

    app.run_polling()

if __name__ == "__main__":
    main()