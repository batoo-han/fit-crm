"""Admin handlers for payment management and CRM integration."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import ADMIN_CHAT_ID
from database.db import get_db_session
from database.models import Payment, Client, TrainingProgram
from services.crm_integration import CRMIntegration
from loguru import logger
from datetime import datetime

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return str(user_id) == ADMIN_CHAT_ID


@router.message(Command("confirm_payment"))
async def cmd_confirm_payment(message: Message):
    """Confirm payment manually (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет прав для этой команды.")
        return
    
    # Parse payment ID from message
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            """
Использование: /confirm_payment <payment_id>

Пример: /confirm_payment 1
            """
        )
        return
    
    try:
        payment_id = int(parts[1])
        db = get_db_session()
        try:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                await message.answer(f"Платеж с ID {payment_id} не найден.")
                return
            
            if payment.status == "completed":
                await message.answer(f"Платеж {payment_id} уже подтвержден.")
                return
            
            # Update payment status
            payment.status = "completed"
            payment.completed_at = datetime.utcnow()
            db.commit()
            
            # Integrate with CRM - move client to paid stage
            try:
                CRMIntegration.move_client_to_paid_stage(
                    client_id=payment.client_id,
                    payment_id=payment.id
                )
            except Exception as e:
                logger.error(f"Error moving client to paid stage in CRM: {e}")
            
            await message.answer(
                f"""
✅ Платеж {payment_id} подтвержден!

Клиент: {payment.client_id}
Сумма: {payment.amount:,.0f}₽
Тип: {payment.payment_type}

Клиент перемещен в этап "Куплена услуга" в CRM.
                """
            )
            
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            await message.answer(f"Ошибка при подтверждении платежа: {e}")
        finally:
            db.close()
            
    except ValueError:
        await message.answer("Неверный формат ID платежа. Используйте число.")


@router.message(Command("assign_program"))
async def cmd_assign_program(message: Message):
    """Assign paid program to client (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет прав для этой команды.")
        return
    
    # Parse command: /assign_program <client_id> <program_type>
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            """
Использование: /assign_program <client_id> <program_type>

Типы программ:
- paid_monthly (1 месяц)
- paid_3month (3 месяца)

Пример: /assign_program 1 paid_monthly
            """
        )
        return
    
    try:
        client_id = int(parts[1])
        program_type = parts[2]
        
        if program_type not in ["paid_monthly", "paid_3month"]:
            await message.answer("Неверный тип программы. Используйте: paid_monthly или paid_3month")
            return
        
        db = get_db_session()
        try:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                await message.answer(f"Клиент с ID {client_id} не найден.")
                return
            
            # Check if client has completed payment
            payment = db.query(Payment).filter(
                Payment.client_id == client_id,
                Payment.status == "completed",
                Payment.payment_type == ("1month" if program_type == "paid_monthly" else "3months")
            ).first()
            
            if not payment:
                await message.answer(
                    f"""
⚠️ Не найден подтвержденный платеж для клиента {client_id}.

Сначала подтвердите платеж командой /confirm_payment
                    """
                )
                return
            
            # Check if program already exists
            existing_program = db.query(TrainingProgram).filter(
                TrainingProgram.client_id == client_id,
                TrainingProgram.program_type == program_type,
                TrainingProgram.is_paid == True
            ).first()
            
            if existing_program:
                await message.answer(
                    f"""
⚠️ У клиента {client_id} уже есть оплаченная программа типа {program_type}.

Используйте CRM для просмотра и редактирования программы.
                    """
                )
                return
            
            await message.answer(
                f"""
Для назначения программы клиенту {client_id} используйте CRM систему.

В CRM вы можете:
1. Просмотреть данные клиента
2. Создать/отредактировать программу
3. Назначить программу клиенту

Программа будет автоматически сохранена в CRM.
                """
            )
            
        except Exception as e:
            logger.error(f"Error assigning program: {e}")
            await message.answer(f"Ошибка: {e}")
        finally:
            db.close()
            
    except ValueError:
        await message.answer("Неверный формат. Используйте: /assign_program <client_id> <program_type>")

