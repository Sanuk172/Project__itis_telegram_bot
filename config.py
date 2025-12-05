import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Database file
DATABASE_FILE = 'bot_database.db'

# Gemini model
# Возможные варианты: 'gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash-exp'
GEMINI_MODEL = 'gemini-2.5-flash'  # Gemini 2.5 Flash

