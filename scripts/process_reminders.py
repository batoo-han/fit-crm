"""Script to process reminders - should be run periodically (e.g., via cron)."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db_session
from services.reminder_service import ReminderService
from loguru import logger
from config import TELEGRAM_BOT_TOKEN
from aiogram import Bot

logger.add("logs/reminders.log", rotation="10 MB", level="INFO")


async def process_reminders_with_bot():
    """Process reminders and send via Telegram bot."""
    try:
        # Initialize bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Get due reminders
        reminders = ReminderService.get_due_reminders(limit=100)
        
        if not reminders:
            logger.info("No due reminders")
            return
        
        logger.info(f"Found {len(reminders)} due reminders")
        
        # Process each reminder
        processed = 0
        for reminder in reminders:
            try:
                from database.db import get_db_session
                from database.models import Client
                
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
                    from services.reminder_service import send_reminder_via_bot
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
        
        # Close bot session
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Error in process_reminders_with_bot: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(process_reminders_with_bot())

