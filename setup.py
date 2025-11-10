"""Setup script for initializing the bot."""
import os
from database.db import init_db
from config import TELEGRAM_BOT_TOKEN
from loguru import logger


def setup():
    """Initialize the bot system."""
    logger.info("Starting bot setup...")
    
    # Check if TELEGRAM_BOT_TOKEN is set
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN is not set! Please configure .env file.")
        print("""
⚠️  WARNING: TELEGRAM_BOT_TOKEN is not configured!

Please:
1. Copy .env.example to .env
2. Edit .env and add your Telegram bot token
3. Run setup again

Get your bot token from @BotFather on Telegram
        """)
        return False
    
    # Create necessary directories
    directories = ["logs", "data", "temp"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False
    
    logger.info("✅ Bot setup completed successfully!")
    print("""
✅ Bot setup completed successfully!

Next steps:
1. Configure your .env file with all necessary credentials
2. Run the bot with: python bot.py

Commands:
  /start - Start bot
  /stats - View statistics (admin only)
    """)
    return True


if __name__ == "__main__":
    setup()
