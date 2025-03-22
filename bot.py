import logging
import os
import vobject
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import config

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global password variable (initialized from config)
PASSWORD = config.PASSWORD

# Helper: verify password
def verify_password(password: str) -> bool:
    return password == PASSWORD

# Convert a file to VCF (vCard) format.
def convert_to_vcf(file_path: str, contact_name: str = "Unknown") -> str:
    try:
        with open(file_path, "rb") as f:
            # Try reading an existing vCard
            contact = vobject.readOne(f)
    except Exception:
        # If reading fails, create a new vCard
        contact = vobject.vCard()
    # Ensure the contact has a full name
    if not hasattr(contact, "fn") or not getattr(contact.fn, "value", None):
        contact.add("fn").value = contact_name
    vcf_filename = f"{contact.fn.value}.vcf"
    with open(vcf_filename, "w") as vcf_file:
        vcf_file.write(contact.serialize())
    return vcf_filename

# /start command: send a greeting message.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a file, and I'll convert it into a vCard (.vcf) file."
    )

# Handler for incoming file messages.
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        return
    # If file appears to be already a VCF, notify the user.
    if document.mime_type and document.mime_type.startswith("text/vcard"):
        await update.message.reply_text("This file is already a VCF!")
        return

    # Download the file and save it locally.
    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)
    contact_name = "Unknown"  # Default contact name (could be enhanced)
    await update.message.reply_text(f"File received: {document.file_name}. Converting...")

    # Convert the file to VCF.
    vcf_filename = convert_to_vcf(file_path, contact_name)

    # Send the converted VCF file back to the user.
    with open(vcf_filename, "rb") as vcf_file:
        await update.message.reply_document(
            document=vcf_file,
            filename=vcf_filename,
            caption=f"Converted file: {vcf_filename}"
        )

    # Clean up temporary files.
    os.remove(file_path)
    os.remove(vcf_filename)

# /changepassword command: only the owner can change the password.
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

# /verify command: to test password verification (optional).
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
    # Create the Application using the bot token from config.
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Register command and message handlers.
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("changepassword", change_password))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    # Start the bot.
    app.run_polling()

if __name__ == "__main__":
    main()