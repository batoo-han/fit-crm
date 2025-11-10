"""Main Telegram bot file for fitness trainer sales system."""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from loguru import logger
from config import TELEGRAM_BOT_TOKEN, LOG_LEVEL
from handlers import start, questionnaire, payment, contacts, faq, admin, admin_payment, my_programs, progress_journal

# Configure logging
logger.add("logs/bot.log", rotation="10 MB", level=LOG_LEVEL)


async def main():
    """Main function to run the bot."""
    # Initialize bot and dispatcher
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(questionnaire.router)
    dp.include_router(payment.router)
    dp.include_router(contacts.router)
    dp.include_router(faq.router)
    dp.include_router(my_programs.router)
    dp.include_router(progress_journal.router)
    dp.include_router(admin.router)
    dp.include_router(admin_payment.router)

    # Set bot commands
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="program", description="Получить программу тренировок"),
        BotCommand(command="my_programs", description="Мои программы"),
        BotCommand(command="progress", description="Дневник параметров"),
        BotCommand(command="price", description="Узнать цены"),
        BotCommand(command="contacts", description="Контакты тренера"),
        BotCommand(command="faq", description="Часто задаваемые вопросы"),
    ]
    await bot.set_my_commands(commands)

    logger.info("Bot started successfully!")
    
    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    asyncio.run(main())
