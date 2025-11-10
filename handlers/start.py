"""Start command handler and main menu."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger
from config import TRAINER_NAME, TRAINER_TELEGRAM, TRAINER_PHONE
from database.db import get_db_session
from database.models import Client, TrainingProgram
from handlers.utils import safe_callback_answer
from services.bot_link_service import use_bot_invite_token
from database.models_crm import ClientBotLink

router = Router()


def get_main_menu_keyboard(has_free_program: bool = False) -> InlineKeyboardMarkup:
    """
    Create main menu keyboard.
    
    Args:
        has_free_program: If True, hide free program button (already received)
    """
    keyboard_buttons = []
    
    # Add free program button only if not received yet
    if not has_free_program:
        keyboard_buttons.append([
            InlineKeyboardButton(text="🎯 Получить бесплатную программу", callback_data="free_program"),
        ])
    
    keyboard_buttons.extend([
        [
            InlineKeyboardButton(text="💰 Узнать цены", callback_data="prices"),
            InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts"),
        ],
        [
            InlineKeyboardButton(text="❓ FAQ", callback_data="faq"),
        ],
        [
            InlineKeyboardButton(text="💼 Купить программу", callback_data="buy_program"),
        ],
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def has_free_program(client_id: int) -> bool:
    """Check if client has received free program."""
    db = get_db_session()
    try:
        program = db.query(TrainingProgram).filter(
            TrainingProgram.client_id == client_id,
            TrainingProgram.program_type == "free_demo"
        ).first()
        return program is not None
    except Exception as e:
        logger.error(f"Error checking free program: {e}")
        return False
    finally:
        db.close()


def format_client_data(client: Client) -> str:
    """Format client data for display."""
    data_parts = []
    
    if client.age:
        data_parts.append(f"Возраст: {client.age} лет")
    if client.gender:
        data_parts.append(f"Пол: {client.gender}")
    if client.height and client.weight:
        data_parts.append(f"Рост: {client.height} см, Вес: {client.weight} кг")
    if client.bmi:
        data_parts.append(f"ИМТ: {client.bmi}")
    if client.experience_level:
        data_parts.append(f"Опыт: {client.experience_level}")
    if client.fitness_goals:
        data_parts.append(f"Цель: {client.fitness_goals}")
    if client.location:
        data_parts.append(f"Место тренировок: {client.location}")
    
    # Ограничения по здоровью (всегда показываем)
    if client.health_restrictions:
        data_parts.append(f"Ограничения по здоровью: {client.health_restrictions}")
    else:
        data_parts.append("Ограничения по здоровью: нет")
    
    # Оборудование (показываем только если место тренировок - дом)
    if client.location and "дом" in client.location.lower():
        if client.equipment:
            data_parts.append(f"Оборудование: {client.equipment}")
        else:
            data_parts.append("Оборудование: не указано")
    
    return "\n".join(data_parts) if data_parts else "Данные не указаны"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    await state.clear()
    
    # Get user info
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    start_payload = ""
    if message.text and " " in message.text:
        start_payload = message.text.split(" ", 1)[1].strip()
    elif hasattr(message, "get_args"):
        start_payload = (message.get_args() or "").strip()
    
    # Create or update client in database
    db = get_db_session()
    client = None
    is_new_client = False
    context_data = None
    source = None
    
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()

        if start_payload:
            # Try to link client via invite token
            linked_client, linked, link_context = use_bot_invite_token(
                db=db,
                token=start_payload,
                telegram_id=user_id,
                username=username,
                first_name=first_name,
            )
            if linked_client:
                client = linked_client
                context_data = link_context
                # Determine source from bot link
                if linked:
                    bot_link = db.query(ClientBotLink).filter(
                        ClientBotLink.invite_token == start_payload
                    ).first()
                    if bot_link:
                        source = bot_link.source
                db.commit()

        if not client:
            client = Client(
                telegram_id=user_id,
                telegram_username=username,
                first_name=first_name,
            )
            db.add(client)
            db.commit()
            is_new_client = True
            logger.info(f"New client registered: {user_id}")

            # Integrate with CRM
            try:
                from services.crm_integration import CRMIntegration
                CRMIntegration.create_client_in_crm(telegram_id=user_id)
            except Exception as e:
                logger.error(f"Error creating client in CRM: {e}")
        else:
            # Update basic info if changed
            if client.first_name != first_name or client.telegram_username != username:
                client.first_name = first_name
                client.telegram_username = username
                db.commit()
            logger.info(f"Existing client started bot: {user_id}")
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Check if client has free program
    has_free = False
    if client and client.id:
        has_free = has_free_program(client.id)
    
    # Generate personalized welcome message
    try:
        from services.welcome_service import WelcomeService
        welcome_text = WelcomeService.get_welcome_message(
            client=client,
            is_new_client=is_new_client,
            context_data=context_data,
            source=source
        )
    except Exception as e:
        logger.error(f"Error generating welcome message: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to default message
        if is_new_client:
            welcome_text = f"""
🏋️ Привет, {first_name}! Меня зовут {TRAINER_NAME}.

Я помогу тебе достичь твоих фитнес-целей! 

🎯 Что я могу предложить:
• Персональную программу тренировок
• План питания с расчетом КБЖУ
• Ежедневную поддержку и мотивацию
• Видео-демонстрации упражнений
• Онлайн-тренировки с тренером

Выбери, что тебе интересно 👇
            """
        else:
            welcome_text = f"""
🏋️ С возвращением, {first_name}!

Я помогу тебе достичь твоих фитнес-целей! 

Выбери, что тебе интересно 👇
            """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(has_free_program=has_free)
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    
    try:
        user_id = callback.from_user.id
        first_name = callback.from_user.first_name
        
        # Check if client has free program
        db = get_db_session()
        has_free = False
        try:
            client = db.query(Client).filter(Client.telegram_id == user_id).first()
            if client and client.id:
                has_free = has_free_program(client.id)
        except Exception as e:
            logger.error(f"Error checking free program: {e}")
        finally:
            db.close()
        
        welcome_text = f"""
🏋️ Главное меню, {first_name}!

Выбери, что тебе интересно 👇
        """
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard(has_free_program=has_free)
        )
        await safe_callback_answer(callback)
    except Exception as e:
        # Handle expired callback queries or message edit errors
        logger.warning(f"Error in back_to_menu: {e}")
        try:
            # Try to send new message instead of editing
            await callback.message.answer(
                welcome_text,
                reply_markup=get_main_menu_keyboard(has_free_program=has_free)
            )
            await safe_callback_answer(callback)
        except Exception as e2:
            logger.error(f"Could not send new message: {e2}")
            await safe_callback_answer(callback)


@router.callback_query(F.data == "data_ok")
async def data_ok(callback: CallbackQuery, state: FSMContext):
    """User confirmed data is correct."""
    user_id = callback.from_user.id
    
    # Get client ID
    db = get_db_session()
    has_free = False
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client and client.id:
            has_free = has_free_program(client.id)
    except Exception as e:
        logger.error(f"Error checking free program: {e}")
    finally:
        db.close()
    
    await callback.message.edit_text(
        """
✅ Отлично! Ваши данные сохранены.

Выбери, что тебе интересно 👇
        """,
        reply_markup=get_main_menu_keyboard(has_free_program=has_free)
    )
    await safe_callback_answer(callback)


@router.callback_query(F.data == "update_data")
async def update_data(callback: CallbackQuery, state: FSMContext):
    """Start questionnaire to update client data."""
    from handlers.questionnaire import QuestionnaireStates
    
    await callback.message.edit_text(
        """
🎯 Отлично! Давайте уточним ваши данные.

Для этого мне нужно узнать немного о тебе. Это займет 2-3 минуты.

Начнем с первого вопроса:

**Сколько вам полных лет?**

Это поможет подобрать безопасную нагрузку.
        """
    )
    await state.set_state(QuestionnaireStates.waiting_age)
    await safe_callback_answer(callback)
