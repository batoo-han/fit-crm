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


async def process_reminders_periodically(bot: Bot):
    """
    Периодически обрабатывать напоминания.
    Запускается каждые 30 минут.
    """
    from services.reminder_service import ReminderService, send_reminder_via_bot
    from database.db import get_db_session
    from database.models import Client
    
    while True:
        try:
            await asyncio.sleep(30 * 60)  # 30 минут
            
            logger.info("Processing reminders...")
            reminders = ReminderService.get_due_reminders(limit=100)
            
            if not reminders:
                logger.info("No due reminders")
                continue
            
            logger.info(f"Found {len(reminders)} due reminders")
            
            processed = 0
            for reminder in reminders:
                try:
                    db = get_db_session()
                    client = db.query(Client).filter(Client.id == reminder.client_id).first()
                    
                    # Check if client has Telegram ID (positive = has Telegram account)
                    if not client or client.telegram_id <= 0:
                        logger.info(f"Client {reminder.client_id} doesn't have Telegram account, marking reminder as sent")
                        ReminderService.mark_reminder_sent(reminder.id)
                        db.close()
                        continue
                    
                    # Process reminder (updates pipeline, creates actions)
                    success = ReminderService.process_reminder(reminder)
                    
                    if success:
                        # Send message via bot if client has Telegram
                        sent = await send_reminder_via_bot(reminder, bot)
                        if sent:
                            ReminderService.mark_reminder_sent(reminder.id)
                            processed += 1
                            logger.info(f"Processed and sent reminder {reminder.id} for client {reminder.client_id}")
                    
                    db.close()
                        
                except Exception as e:
                    logger.error(f"Error processing reminder {reminder.id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            logger.info(f"Processed {processed} reminders")
            
        except Exception as e:
            logger.error(f"Error in process_reminders_periodically: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(60)  # Wait 1 minute before retrying


async def check_payments_periodically():
    """
    Периодически проверять статус платежей.
    Запускается каждые 5 минут.
    """
    from services.payment_service import PaymentService
    
    while True:
        try:
            await asyncio.sleep(5 * 60)  # 5 минут
            
            logger.info("Checking pending payments...")
            updated_count = await PaymentService.check_pending_payments_async(limit=100)
            
            if updated_count > 0:
                logger.info(f"Updated {updated_count} payment statuses")
            
        except Exception as e:
            logger.error(f"Error in check_payments_periodically: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(60)  # Wait 1 minute before retrying


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
    
    # Start reminder processing task
    asyncio.create_task(process_reminders_periodically(bot))
    
    # Start payment status checking task
    asyncio.create_task(check_payments_periodically())
    
    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    asyncio.run(main())
