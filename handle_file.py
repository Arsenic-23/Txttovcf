import os
import vobject
from telegram import Update
from telegram.ext import ContextTypes
from receive_file import ask_for_contact_name

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles uploaded files, checks format, and prompts for missing contact names."""
    
    document = update.message.document
    if not document:
        return
    
    # Check if the file is already a VCF
    if document.mime_type and "vcard" in document.mime_type.lower():
        await update.message.reply_text("✅ This file is already a VCF!")
        return

    # Download the file
    file = await document.get_file()
    file_path = f"{document.file_unique_id}_{document.file_name}"
    await file.download_to_drive(file_path)

    # Ask user for missing contact names
    await ask_for_contact_name(update, context, file_path)