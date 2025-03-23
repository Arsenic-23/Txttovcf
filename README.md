# **Telegram vCard Converter Bot**  

This is a Telegram bot that converts any sent file into a **vCard (.vcf) file**.  
It features a **secure password system**, ensuring that only the **owner** (identified by their Telegram User ID) can change the password.  
The bot is **fully asynchronous**, ensuring fast performance and seamless operation. It is optimized for **deployment on Koyeb**.

---

## **Files & Structure**  

| File | Description |
|------|------------|
| **config.py** | Stores configuration variables (bot token, owner ID, password). |
| **bot.py** | Main bot logic, including authentication and file conversion. |
| **requirements.txt** | Lists all required dependencies for the bot. |
| **Procfile** | Defines the command to run the bot on Koyeb. |
| **.gitignore** | (Optional) Specifies files and directories to ignore in the repository. |
| **README.md** | (Optional) Provides setup instructions and project details. |

---

## **Setup & Deployment**  

### **1. Clone the Repository**  
```bash
git clone https://github.com/yourusername/telegram-bot.git
cd telegram-bot
```

### **2. Install Dependencies**  
```bash
pip install -r requirements.txt
```

### **3. Configure the Bot**  
- Open **`config.py`** and **replace** the placeholder values:  
  - `BOT_TOKEN` → Your **Telegram Bot Token**  
  - `OWNER_ID` → Your **Telegram User ID**  

### **4. Run the Bot**  
```bash
python bot.py
```

### **5. Deploy on Koyeb**  
- Create a **new service** on Koyeb.  
- Connect your **GitHub repository**.  
- Deploy using the provided **Procfile**.  

---

## **Commands**  

| Command | Description |
|---------|------------|
| `/start` | Starts the bot and shows usage instructions. |
| `/changepassword <new_password>` | (Owner only) Changes the bot's password. |
| `Send a file` | Prompts for a contact name and converts the file to `.vcf`. |

---

## **Features**  
✅ **Secure Password System** (Only the owner can change it)  
✅ **Asynchronous & Fast** for quick file conversion  
✅ **VCF File Support** with automatic contact name handling  
✅ **Optimized for Koyeb** deployment  

---

## **Need Help?**  
If you encounter any issues, feel free to **open an issue** on GitHub or contact the bot owner.