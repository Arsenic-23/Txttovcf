import logging
import os
import vobject
import sys
import psutil
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import config

# Dummy HTTP Server for Koyeb Health Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_dummy_http_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthCheckHandler)
    server.serve_forever()

# Run HTTP server in a separate thread (so it doesn’t block the bot)
threading.Thread(target=start_dummy_http_server, daemon=True).start()

# Prevent multiple instances
def check_instance():
    script_name = os.path.basename(__file__)
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if script_name in proc.info['cmdline']:
            if proc.pid != os.getpid():
                print("Another instance is running. Exiting...")
                sys.exit()

check_instance()

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global password variable
PASSWORD = config.PASSWORD

# Verify password
def verify_password(password: str) -> bool:
    return password == PASSWORD

# Convert file to VCF
def convert_to_vcf(file_path: str, contact_name: str = "Unknown") -> str:
    try:
        with open(file_path, "rb") as f:
            contact = vobject.readOne(f)
    except Exception:
        contact = vobject.vCard()
    
    if not hasattr(contact, "fn") or not getattr(contact.fn, "value", None):
        contact.add("fn").value = contact_name

    vcf_filename = f"{contact.fn.value}.vcf"
    with open(vcf_filename, "w") as vcf_file:
        vcf_file.write(contact.serialize())
    
    return vcf_filename

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a file, and I'll convert it into a vCard (.vcf) file.")

# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        return

    if document.mime_type and document.mime_type.startswith("text/vcard"):
        await update.message.reply_text("This file is already a VCF!")
        return

    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)
    
    contact_name = "Unknown"
    await update.message.reply_text(f"File received: {document.file_name}. Converting...")

    vcf_filename = convert_to_vcf(file_path, contact_name)

    with open(vcf_filename, "rb") as vcf_file:
        await update.message.reply_document(document=vcf_file, filename=vcf_filename, caption=f"Converted file: {vcf_filename}")

    os.remove(file_path)
    os.remove(vcf_filename)

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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("changepassword", change_password))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
