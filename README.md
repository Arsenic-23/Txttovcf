# Telegram vCard Converter Bot

This is a Telegram bot that converts any sent file to a vCard (.vcf) file.  
It features a secure password system where only the owner (identified by their Telegram user ID) can change the password. The bot is built with asynchronous methods for fast performance and is ready to be deployed on Koyeb.

## Files

- **config.py**: Stores configuration variables (bot token, owner ID, password).
- **bot.py**: Main bot code containing all functionality.
- **requirements.txt**: Lists all necessary dependencies.
- **Procfile**: Instructs Koyeb on how to run the bot.
- **.gitignore**: (Optional) Specifies files and directories to ignore in the repository.
- **README.md**: (Optional) Project description and setup instructions.

## Setup and Deployment

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/yourusername/telegram-bot.git
   cd telegram-bot