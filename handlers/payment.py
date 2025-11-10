"""Payment and pricing handlers."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from config import (
    PRICE_CONSULTATION,
    PRICE_ONLINE_1_MONTH,
    PRICE_ONLINE_3_MONTHS,
    TRAINER_TELEGRAM,
    TRAINER_PHONE,
    YOOKASSA_SHOP_ID,
    YOOKASSA_SECRET_KEY,
)
from database.db import get_db_session
from database.models import Payment, Client
from services.payments_yookassa import create_yookassa_payment

router = Router()


def get_prices_keyboard() -> InlineKeyboardMarkup:
    """Create pricing keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📞 Консультация (1 час) - 1 490₽", callback_data="buy_consultation"),
        ],
        [
            InlineKeyboardButton(text="💼 Онлайн-сопровождение (1 месяц) - 14 999₽", callback_data="buy_1month"),
        ],
        [
            InlineKeyboardButton(text="🏆 Онлайн-сопровождение (3 месяца) - 34 999₽", callback_data="buy_3months"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
        ],
    ])


@router.message(F.text == "/price")
async def cmd_price(message: Message):
    """Handle /price command."""
    prices_text = """
💰 Тарифы и услуги

📞 **Онлайн-консультация (1 час)** - 1 490₽
Персональная консультация, анализ текущего состояния, рекомендации

💼 **Персональное онлайн-сопровождение (1 месяц)** - 14 999₽
• Индивидуальный план тренировок
• Персонализированный план питания с расчетом КБЖУ
• 3 онлайн-тренировки с тренером
• Ежедневная связь для отчетности
• Видео-демонстрации упражнений
• Анализ техники выполнения
• Рекомендации по спортивным добавкам

🏆 **Персональное онлайн-сопровождение (3 месяца)** - 34 999₽
Экономия: 9 998₽
• Все преимущества месячного сопровождения
• Поэтапное усложнение программы
• 9 онлайн-тренировок
• Расширенные рекомендации по восстановлению
• Материалы по психологии формирования привычек
• Анализ прогресса

Выбери подходящий вариант:
    """
    
    await message.answer(
        prices_text,
        reply_markup=get_prices_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    """Show pricing information."""
    prices_text = """
💰 Тарифы и услуги

📞 **Онлайн-консультация (1 час)** - 1 490₽
Персональная консультация, анализ текущего состояния, рекомендации

💼 **Персональное онлайн-сопровождение (1 месяц)** - 14 999₽
• Индивидуальный план тренировок
• Персонализированный план питания с расчетом КБЖУ
• 3 онлайн-тренировки с тренером
• Ежедневная связь для отчетности
• Видео-демонстрации упражнений
• Анализ техники выполнения
• Рекомендации по спортивным добавкам

🏆 **Персональное онлайн-сопровождение (3 месяца)** - 34 999₽
Экономия: 9 998₽
• Все преимущества месячного сопровождения
• Поэтапное усложнение программы
• 9 онлайн-тренировок
• Расширенные рекомендации по восстановлению
• Материалы по психологии формирования привычек
• Анализ прогресса

Выбери подходящий вариант:
    """
    
    await callback.message.edit_text(
        prices_text,
        reply_markup=get_prices_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "buy_program")
async def buy_program_menu(callback: CallbackQuery):
    """Show buy program menu."""
    await show_prices(callback)


@router.callback_query(F.data.startswith("buy_"))
async def process_payment(callback: CallbackQuery):
    """Process payment selection."""
    user_id = callback.from_user.id
    payment_type = callback.data
    
    # Map payment types to prices
    price_map = {
        "consultation": PRICE_CONSULTATION,
        "1month": PRICE_ONLINE_1_MONTH,
        "3months": PRICE_ONLINE_3_MONTHS
    }
    
    payment_type_short = payment_type.replace("buy_", "")
    price = price_map[payment_type_short]
    
    # Save payment intent to database
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client:
            payment = Payment(
                client_id=client.id,
                amount=price,
                payment_type=payment_type_short,
                status="pending",
                payment_method=("yookassa" if (YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY) else "manual"),
            )
            db.add(payment)
            db.commit()
            logger.info(f"Payment intent created: {payment.id} for client {client.id}")

            # Try to create YooKassa payment if credentials exist
            payment_url = None
            if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
                try:
                    # Формируем описание для чека
                    description_map = {
                        "consultation": "Онлайн-консультация (1 час)",
                        "1month": "Онлайн-сопровождение (1 месяц)",
                        "3months": "Онлайн-сопровождение (3 месяца)"
                    }
                    
                    yk = await create_yookassa_payment(
                        amount=price,
                        description=description_map.get(payment_type_short, f"Услуга тренера"),
                        payment_id=str(payment.id),
                        metadata={"client_id": client.id, "telegram_id": user_id, "type": payment_type_short},
                        customer_email=None  # Можно добавить email клиента, если есть
                    )
                    if yk and yk.get("confirmation"):
                        payment.payment_id = yk.get("id")
                        db.commit()
                        payment_url = yk["confirmation"].get("confirmation_url")
                except Exception as e:
                    logger.error(f"YooKassa error: {e}")
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        db.close()
    
    # Show payment options
    if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY and 'payment_url' in locals() and payment_url:
        await callback.message.edit_text(
            f"""
💳 Оплата через ЮKassa

Сумма к оплате: {price:,}₽

Нажми кнопку ниже, чтобы перейти к безопасной оплате на стороне ЮKassa.
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Оплатить картой (ЮKassa)", url=payment_url)],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )
    else:
        await callback.message.edit_text(
            f"""
💳 Для оплаты свяжись с тренером:

📱 Telegram: {TRAINER_TELEGRAM}
📞 WhatsApp: {TRAINER_PHONE}

💬 Напиши "Хочу купить программу" и укажи выбранный тариф.

После оплаты ты получишь:
✅ Персональную программу тренировок
✅ План питания
✅ Доступ к онлайн-тренировкам
✅ Ежедневную поддержку

Сумма к оплате: {price:,}₽
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Написать в Telegram", url=f"https://t.me/{TRAINER_TELEGRAM.replace('@', '')}")],
                [InlineKeyboardButton(text="📞 Написать в WhatsApp", url=f"https://wa.me/{TRAINER_PHONE.replace('+', '')}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )
    await callback.answer()
