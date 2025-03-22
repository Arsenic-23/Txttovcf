import os
import vobject
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

CONTACT_NAME = 0
file_storage = {}

async def ask_for_contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    file_storage[update.message.chat_id] = file_path
    await update.message.reply_text("Please enter a name for the contact:")
    return CONTACT_NAME

async def convert_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    contact_name = update.message.text.strip()

    if chat_id not in file_storage:
        await update.message.reply_text("No file found for conversion.")
        return ConversationHandler.END

    file_path = file_storage.pop(chat_id)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            contact = vobject.readOne(f)
    except Exception:
        contact = vobject.vCard()

    if not hasattr(contact, "fn") or not getattr(contact.fn, "value", None):
        contact.add("fn").value = contact_name

    vcf_filename = f"{contact_name}.vcf"
    with open(vcf_filename, "w", encoding="utf-8") as vcf_file:
        vcf_file.write(contact.serialize())

    with open(vcf_filename, "rb") as vcf_file:
        await update.message.reply_document(document=vcf_file, filename=vcf_filename, caption=f"Converted file: {vcf_filename}")

    os.remove(file_path)
    os.remove(vcf_filename)

    return ConversationHandler.END