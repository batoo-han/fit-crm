"""Admin handlers for bot management."""
from aiogram import Router, F
from aiogram.types import Message
from config import ADMIN_CHAT_ID
from database.db import get_db_session
from database.models import Client, Lead, Payment
from loguru import logger

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return str(user_id) == ADMIN_CHAT_ID


@router.message(F.text == "/stats")
async def cmd_stats(message: Message):
    """Show bot statistics."""
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет прав для этой команды.")
        return
    
    db = get_db_session()
    try:
        total_clients = db.query(Client).count()
        qualified_clients = db.query(Client).filter(Client.status == "qualified").count()
        total_leads = db.query(Lead).count()
        total_payments = db.query(Payment).count()
        completed_payments = db.query(Payment).filter(Payment.status == "completed").count()
        total_revenue = db.query(Payment).filter(Payment.status == "completed").all()
        revenue = sum(p.amount for p in total_revenue)
        
        stats_text = f"""
📊 Статистика бота

👥 **Клиенты:**
• Всего зарегистрировано: {total_clients}
• Прошли опросник: {qualified_clients}

🎯 **Лиды:**
• Всего лидов: {total_leads}

💰 **Платежи:**
• Всего платежей: {total_payments}
• Завершено: {completed_payments}
• Выручка: {revenue:,.0f}₽

📈 Конверсия: {((qualified_clients / total_clients * 100) if total_clients > 0 else 0):.1f}%
        """
        
        await message.answer(stats_text)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.answer("Ошибка при получении статистики.")
    finally:
        db.close()
