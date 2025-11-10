"""Service for managing automated reminders for clients."""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from database.db import get_db_session
from database.models import Client, TrainingProgram
from database.models_crm import Reminder, ReminderType
from services.pipeline_service import PipelineAutomation
from services.crm_integration import CRMIntegration
from config import PRICE_ONLINE_1_MONTH, PRICE_ONLINE_3_MONTHS, TRAINER_NAME, TRAINER_TELEGRAM, TRAINER_PHONE


class ReminderService:
    """Service for creating and sending reminders to clients."""
    
    @staticmethod
    def create_free_program_reminders(client_id: int, program_id: int, program_assigned_at: datetime) -> List[int]:
        """
        Create reminders for free program recipients.
        
        Args:
            client_id: Client ID
            program_id: Program ID
            program_assigned_at: When the program was assigned
            
        Returns:
            List of reminder IDs
        """
        db = get_db_session()
        reminder_ids = []
        try:
            # Reminder after 3 days - check progress
            reminder_3d = Reminder(
                client_id=client_id,
                program_id=program_id,
                reminder_type=ReminderType.FREE_PROGRAM_DAY_3.value,
                scheduled_at=program_assigned_at + timedelta(days=3),
                message_text=get_reminder_message(ReminderType.FREE_PROGRAM_DAY_3.value)
            )
            db.add(reminder_3d)
            reminder_ids.append(reminder_3d.id)
            
            # Reminder after 5 days - motivation
            reminder_5d = Reminder(
                client_id=client_id,
                program_id=program_id,
                reminder_type=ReminderType.FREE_PROGRAM_DAY_5.value,
                scheduled_at=program_assigned_at + timedelta(days=5),
                message_text=get_reminder_message(ReminderType.FREE_PROGRAM_DAY_5.value)
            )
            db.add(reminder_5d)
            reminder_ids.append(reminder_5d.id)
            
            # Reminder after 7 days - offer paid program
            reminder_7d = Reminder(
                client_id=client_id,
                program_id=program_id,
                reminder_type=ReminderType.FREE_PROGRAM_DAY_7.value,
                scheduled_at=program_assigned_at + timedelta(days=7),
                message_text=get_reminder_message(ReminderType.FREE_PROGRAM_DAY_7.value)
            )
            db.add(reminder_7d)
            reminder_ids.append(reminder_7d.id)
            
            db.commit()
            logger.info(f"Created {len(reminder_ids)} reminders for client {client_id}, program {program_id}")
            
            # Move client to "Принимают решение" stage after 7 days
            # This will be handled when reminder is sent
            
        except Exception as e:
            logger.error(f"Error creating reminders: {e}")
            db.rollback()
        finally:
            db.close()
        
        return reminder_ids
    
    @staticmethod
    def get_due_reminders(limit: int = 100) -> List[Reminder]:
        """
        Get reminders that are due to be sent.
        
        Args:
            limit: Maximum number of reminders to return
            
        Returns:
            List of reminders
        """
        db = get_db_session()
        try:
            now = datetime.utcnow()
            reminders = db.query(Reminder).filter(
                Reminder.is_sent == False,
                Reminder.scheduled_at <= now
            ).limit(limit).all()
            return reminders
        except Exception as e:
            logger.error(f"Error getting due reminders: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def mark_reminder_sent(reminder_id: int, sent_at: Optional[datetime] = None) -> bool:
        """
        Mark reminder as sent.
        
        Args:
            reminder_id: Reminder ID
            sent_at: When it was sent (defaults to now)
            
        Returns:
            True if successful
        """
        db = get_db_session()
        try:
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if reminder:
                reminder.is_sent = True
                reminder.sent_at = sent_at or datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking reminder sent: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def process_reminder(reminder: Reminder) -> bool:
        """
        Process a reminder - send message and update pipeline if needed.
        
        Args:
            reminder: Reminder to process
            
        Returns:
            True if successful
        """
        db = get_db_session()
        try:
            client = db.query(Client).filter(Client.id == reminder.client_id).first()
            if not client:
                logger.warning(f"Client {reminder.client_id} not found for reminder {reminder.id}")
                return False
            
            # Check if client has Telegram ID (positive = has Telegram account)
            if client.telegram_id <= 0:
                logger.info(f"Client {client.id} doesn't have Telegram account, skipping reminder {reminder.id}")
                # Mark as sent anyway to avoid retrying
                ReminderService.mark_reminder_sent(reminder.id)
                return True
            
            # Send reminder via Telegram bot (will be handled by bot service)
            # For now, we just mark it as sent and update pipeline
            
            # Update pipeline based on reminder type
            automation = PipelineAutomation(db)
            
            if reminder.reminder_type == ReminderType.FREE_PROGRAM_DAY_7.value:
                # Move to "Принимают решение" stage after 7 days
                automation.move_client_to_stage_by_name(
                    client=client,
                    stage_name="Принимают решение",
                    notes=f"Автоматическое перемещение после завершения бесплатной недели (reminder {reminder.id})"
                )
                
                # Create action
                from database.models_crm import ClientAction, ActionType
                action = ClientAction(
                    client_id=client.id,
                    action_type=ActionType.FOLLOW_UP.value,
                    action_date=datetime.utcnow(),
                    description="Отправлено предложение оплаты после бесплатной недели",
                    created_by=None  # Система
                )
                db.add(action)
                db.commit()
            
            # Mark reminder as sent
            ReminderService.mark_reminder_sent(reminder.id)
            logger.info(f"Processed reminder {reminder.id} for client {client.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing reminder {reminder.id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()


def get_reminder_message(reminder_type: str) -> str:
    """
    Get message text for reminder type.
    
    Args:
        reminder_type: Type of reminder
        
    Returns:
        Message text
    """
    messages = {
        ReminderType.FREE_PROGRAM_DAY_3.value: f"""
🏋️ Привет! Это {TRAINER_NAME}.

Прошло 3 дня с момента выдачи бесплатной программы. Как дела? Есть вопросы по тренировкам?

Если нужна помощь - напишите мне! 💪
        """,
        ReminderType.FREE_PROGRAM_DAY_5.value: f"""
💪 Привет! {TRAINER_NAME} на связи.

Уже 5 дней тренируетесь? Отлично! Помните - регулярность - залог успеха.

Продолжайте в том же духе! Если есть вопросы - обращайтесь. 🚀
        """,
        ReminderType.FREE_PROGRAM_DAY_7.value: f"""
🎯 Привет! {TRAINER_NAME} снова с вами.

Прошла неделя тренировок! Как вам программа? Видите результаты?

💼 Для максимального эффекта рекомендую приобрести полную персональную программу:
• Индивидуальные упражнения под ваши цели
• План питания с расчетом КБЖУ
• Онлайн-тренировки с тренером
• Ежедневная поддержка и мотивация

💰 Цены:
• 1 месяц: {PRICE_ONLINE_1_MONTH:,}₽
• 3 месяца: {PRICE_ONLINE_3_MONTHS:,}₽ (экономия {PRICE_ONLINE_1_MONTH * 3 - PRICE_ONLINE_3_MONTHS:,}₽)

Готовы продолжить? Напишите мне или используйте команду /buy_program
        """,
    }
    return messages.get(reminder_type, "Напоминание от фитнес-тренера.")


async def send_reminder_via_bot(reminder: Reminder, bot) -> bool:
    """
    Send reminder message via Telegram bot.
    
    Args:
        reminder: Reminder to send
        bot: Telegram bot instance
        
    Returns:
        True if successful
    """
    db = None
    try:
        db = get_db_session()
        client = db.query(Client).filter(Client.id == reminder.client_id).first()
        if not client or client.telegram_id <= 0:
            return False
        
        message_text = reminder.message_text or get_reminder_message(reminder.reminder_type)
        
        # Add inline keyboard for day 7 reminder
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        if reminder.reminder_type == ReminderType.FREE_PROGRAM_DAY_7.value:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💼 Купить программу", callback_data="buy_program")],
                [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
            ])
        else:
            keyboard = None
        
        # Send message
        await bot.send_message(
            chat_id=client.telegram_id,
            text=message_text,
            reply_markup=keyboard
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending reminder via bot: {e}")
        return False
    finally:
        if db:
            db.close()

