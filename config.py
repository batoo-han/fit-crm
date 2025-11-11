"""Configuration module for the fitness trainer bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # optional for social posts

# Social networks
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")  # numeric ID or screen name, e.g. -123456789 for community

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Google Sheets Configuration
# Google Sheets - using public CSV access (no credentials needed)
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # Optional, extracted from URL automatically

# AI Configuration
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_GPT_MODEL = os.getenv("YANDEX_GPT_MODEL", "yandexgpt-lite")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

# ProxyAPI Configuration (for OpenAI)
PROXYAPI_BASE_URL = os.getenv("PROXYAPI_BASE_URL", "https://api.proxyapi.ru/openai/v1")
PROXYAPI_API_KEY = os.getenv("PROXYAPI_API_KEY")

# AmoCRM Configuration
AMOCRM_DOMAIN = os.getenv("AMOCRM_DOMAIN")
AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID")
AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET")

# Payment Configuration (YooKassa)
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "https://www.batoohan.ru/pay/return")

# Tinkoff (optional, used when selected as active provider)
TINKOFF_TERMINAL_KEY = os.getenv("TINKOFF_TERMINAL_KEY")
TINKOFF_SECRET_KEY = os.getenv("TINKOFF_SECRET_KEY")
TINKOFF_RETURN_URL = os.getenv("TINKOFF_RETURN_URL", "https://www.batoohan.ru/pay/return")
# amoCRM optional integration
AMOCRM_ENABLED = os.getenv("AMOCRM_ENABLED", "false").lower() in ("1", "true", "yes")
AMOCRM_DOMAIN = os.getenv("AMOCRM_DOMAIN")  # e.g., example.amocrm.ru
AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID")
AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET")
AMOCRM_REDIRECT_URI = os.getenv("AMOCRM_REDIRECT_URI")

# Trainer Information
TRAINER_NAME = os.getenv("TRAINER_NAME", "Данила Цыганков")
TRAINER_TELEGRAM = os.getenv("TRAINER_TELEGRAM", "@DandK_FitBody")
TRAINER_PHONE = os.getenv("TRAINER_PHONE", "+79099202195")
TRAINER_EMAIL = os.getenv("TRAINER_EMAIL")

# Training Plan URLs
TRAINING_PLAN_WOMEN = os.getenv(
    "TRAINING_PLAN_WOMEN",
    "https://docs.google.com/spreadsheets/d/1RsW_faEZ5y_tYNU3SZtcbFJLgbymAI05LKX8RrI0UYw/edit"
)
TRAINING_PLAN_MEN = os.getenv(
    "TRAINING_PLAN_MEN",
    "https://docs.google.com/spreadsheets/d/1cjCqIos0QOBH9_-2MiQMCCbV70Ct8qvS50jaBF4_ZPc/edit"
)

# Pricing (in RUB)
PRICE_CONSULTATION = int(os.getenv("PRICE_CONSULTATION", "1490"))
PRICE_ONLINE_1_MONTH = int(os.getenv("PRICE_ONLINE_1_MONTH", "14999"))
PRICE_ONLINE_3_MONTHS = int(os.getenv("PRICE_ONLINE_3_MONTHS", "34999"))

# Bot Settings
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
