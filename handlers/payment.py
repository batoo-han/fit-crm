"""Payment and pricing handlers."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
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
from services.payment_gateway import PaymentGateway
from services.promo_service import PromoService
from services.payment_gateway import PaymentGateway

router = Router()


class PromoStates(StatesGroup):
    waiting_for_code = State()


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
            InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="enter_promo"),
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


@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext):
    """Ask user to enter promo code and remember we're in promo mode."""
    await state.update_data(intended_payment_type=None)
    await state.set_state(PromoStates.waiting_for_code)
    await callback.message.edit_text(
        "🎟 Введите промокод одним сообщением (например, FIT2025). Чтобы отменить — нажмите «Назад».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="prices")]]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
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

    # If we are in promo entering flow, remember intended type and ask for code
    current_state = await state.get_state()
    if current_state == PromoStates.waiting_for_code:
        await state.update_data(intended_payment_type=payment_type_short)
        await callback.message.edit_text(
            f"🎟 Введите промокод для тарифа «{payment_type_short}» или нажмите «Пропустить».",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⏭ Пропустить промокод", callback_data="skip_promo")
            ], [InlineKeyboardButton(text="⬅️ Назад", callback_data="prices")]]),
        )
        await callback.answer()
        return
    
    # Save payment intent to database
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client:
            # Check default promo code from settings
            default_promo = None
            discount_amount = None
            final_amount = price
            try:
                settings = PaymentGateway.get_settings(db)
                default_promo = (settings.get("default_promo_code") or "").strip().upper() or None
                if default_promo:
                    try:
                        PromoService.validate_code(db, default_promo, client)
                        disc = PromoService.apply_discount(price, PromoService.get_code(db, default_promo))
                        discount_amount = disc["discount"]
                        final_amount = disc["final_amount"]
                    except Exception as _e:
                        default_promo = None
            except Exception as _e:
                default_promo = None

            payment = Payment(
                client_id=client.id,
                amount=price,
                final_amount=final_amount,
                discount_amount=discount_amount,
                promo_code=default_promo,
                payment_type=payment_type_short,
                status="pending",
                payment_method=("yookassa" if (YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY) else "manual"),
            )
            db.add(payment)
            db.commit()
            logger.info(f"Payment intent created: {payment.id} for client {client.id}")

            # Try to create payment via active provider
            payment_url = None
            try:
                # Формируем описание для чека
                description_map = {
                    "consultation": "Онлайн-консультация (1 час)",
                    "1month": "Онлайн-сопровождение (1 месяц)",
                    "3months": "Онлайн-сопровождение (3 месяца)"
                }
                pay = await PaymentGateway.create_payment(
                    db=db,
                    provider=None,  # autodetect from WebsiteSettings.payment_provider
                    amount=final_amount,
                    description=description_map.get(payment_type_short, f"Услуга тренера"),
                    internal_payment_id=str(payment.id),
                    customer_email=None,
                )
                if pay and pay.get("confirmation"):
                    payment.payment_id = pay.get("id")
                    db.commit()
                    payment_url = pay["confirmation"].get("confirmation_url")
            except Exception as e:
                logger.error(f"Payment create error: {e}")
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        db.close()
    
    # Show payment options
    if 'payment_url' in locals() and payment_url:
        await callback.message.edit_text(
            f"""
💳 Оплата

Сумма к оплате: {price:,}₽

Нажми кнопку ниже, чтобы перейти к безопасной оплате.
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Оплатить картой", url=payment_url)],
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


@router.callback_query(F.data == "skip_promo")
async def skip_promo(callback: CallbackQuery, state: FSMContext):
    """Skip promo and show price options again."""
    await state.clear()
    await show_prices(callback)


@router.message(PromoStates.waiting_for_code)
async def receive_promo_code(message: Message, state: FSMContext):
    """Receive promo code, validate and proceed to create discounted payment."""
    code = (message.text or "").strip().upper()
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == message.from_user.id).first()
        if not client:
            await message.answer("Не удалось определить клиента. Попробуйте ещё раз через меню цен.")
            await state.clear()
            return
        # Determine intended payment type or ask to choose
        data = await state.get_data()
        intended = data.get("intended_payment_type")
        if not intended:
            await message.answer("Выберите тариф и затем нажмите «Ввести промокод».")
            await state.clear()
            return

        # Base prices
        price_map = {
            "consultation": PRICE_CONSULTATION,
            "1month": PRICE_ONLINE_1_MONTH,
            "3months": PRICE_ONLINE_3_MONTHS,
        }
        base_amount = price_map[intended]

        # Validate promo
        try:
            result = PromoService.validate_code(db, code, client)
        except ValueError as e:
            await message.answer(f"Промокод не применён: {e}")
            await state.clear()
            return
        promo = result["promo"]
        disc = PromoService.apply_discount(base_amount, promo)
        final_amount = disc["final_amount"]
        discount_amount = disc["discount"]

        # Create payment with promo fields
        payment = Payment(
            client_id=client.id,
            amount=base_amount,
            final_amount=final_amount,
            discount_amount=discount_amount,
            promo_code=code,
            payment_type=intended,
            status="pending",
            payment_method=("yookassa" if (YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY) else "manual"),
        )
        db.add(payment)
        db.commit()

        # Create YooKassa payment
        payment_url = None
        if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
            try:
                description_map = {
                    "consultation": "Онлайн-консультация (1 час)",
                    "1month": "Онлайн-сопровождение (1 месяц)",
                    "3months": "Онлайн-сопровождение (3 месяца)",
                }
                metadata = {
                    "client_id": client.id,
                    "telegram_id": message.from_user.id,
                    "type": intended,
                    "promo_code": code,
                    "discount_amount": discount_amount,
                    "final_amount": final_amount,
                }
                yk = await create_yookassa_payment(
                    amount=final_amount,
                    description=description_map.get(intended, "Услуга тренера"),
                    payment_id=str(payment.id),
                    metadata=metadata,
                    customer_email=None,
                )
                if yk and yk.get("confirmation"):
                    payment.payment_id = yk.get("id")
                    db.commit()
                    payment_url = yk["confirmation"].get("confirmation_url")
            except Exception as e:
                logger.error(f"YooKassa error: {e}")

        await state.clear()

        if payment_url:
            await message.answer(
                f"🎟 Промокод применён. Скидка: {int(discount_amount)}₽. К оплате: {int(final_amount)}₽.\nПерейдите по ссылке для оплаты:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оплатить (ЮKassa)", url=payment_url)]]),
            )
        else:
            await message.answer(
                f"🎟 Промокод применён. Скидка: {int(discount_amount)}₽. К оплате: {int(final_amount)}₽.\nДля оплаты свяжитесь с тренером.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]]),
            )
    finally:
        db.close()
