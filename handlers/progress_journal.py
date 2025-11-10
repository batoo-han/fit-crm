"""Progress journal handler for clients to track their measurements."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from database.db import get_db_session
from database.models import Client, TrainingProgram
from database.models_crm import ProgressJournal
from services.crm_integration import CRMIntegration
from datetime import datetime

router = Router()


class ProgressStates(StatesGroup):
    """States for progress journal flow."""
    waiting_period = State()
    waiting_weight = State()
    waiting_measurements = State()


@router.message(Command("progress"))
async def cmd_progress(message: Message, state: FSMContext):
    """Start progress journal entry."""
    user_id = message.from_user.id
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if not client:
            await message.answer("Сначала пройдите опросник /program")
            return
        
        # Check if client has active program
        if not client.current_program_id:
            await message.answer(
                """
📋 У вас пока нет активной программы тренировок.

Используйте /program чтобы получить программу!
                """
            )
            return
        
        # Show period selection
        await message.answer(
            """
📊 Дневник параметров

Выберите период для записи измерений:
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📅 До начала программы", callback_data="period_before")],
                [InlineKeyboardButton(text="📅 1 неделя", callback_data="period_week_1")],
                [InlineKeyboardButton(text="📅 2 неделя", callback_data="period_week_2")],
                [InlineKeyboardButton(text="📅 3 неделя", callback_data="period_week_3")],
                [InlineKeyboardButton(text="📅 4 неделя", callback_data="period_week_4")],
                [InlineKeyboardButton(text="📅 5-8 недели", callback_data="period_weeks_5_8")],
                [InlineKeyboardButton(text="📅 9-12 недели", callback_data="period_weeks_9_12")],
                [InlineKeyboardButton(text="📅 После завершения", callback_data="period_after")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )
        await state.set_state(ProgressStates.waiting_period)
        
    except Exception as e:
        logger.error(f"Error in progress command: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()


@router.callback_query(F.data.startswith("period_"), ProgressStates.waiting_period)
async def process_period(callback: CallbackQuery, state: FSMContext):
    """Process period selection."""
    period_map = {
        "period_before": "before",
        "period_week_1": "week_1",
        "period_week_2": "week_2",
        "period_week_3": "week_3",
        "period_week_4": "week_4",
        "period_weeks_5_8": "week_5",  # Можно расширить для выбора конкретной недели
        "period_weeks_9_12": "week_9",
        "period_after": "after"
    }
    
    period_code = period_map.get(callback.data, "before")
    await state.update_data(period=period_code)
    
    await callback.message.edit_text(
        """
📊 Введите ваш вес (в кг):

Например: 75.5
        """
    )
    await state.set_state(ProgressStates.waiting_weight)
    await callback.answer()


@router.message(ProgressStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Process weight input."""
    try:
        weight = float(message.text.replace(",", "."))
        await state.update_data(weight=weight)
        
        await message.answer(
            """
📊 Теперь введите обхваты (в см):

Формат: грудь, талия, низ живота, ягодицы

Например: 95, 80, 85, 100

Или просто нажмите "Пропустить", если не хотите вводить сейчас.
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_measurements")],
            ])
        )
        await state.set_state(ProgressStates.waiting_measurements)
        
    except ValueError:
        await message.answer("Пожалуйста, введите вес числом. Например: 75.5")


@router.callback_query(F.data == "skip_measurements", ProgressStates.waiting_measurements)
async def skip_measurements(callback: CallbackQuery, state: FSMContext):
    """Skip measurements and save progress entry."""
    await save_progress_entry(callback, state, measurements={})


@router.message(ProgressStates.waiting_measurements)
async def process_measurements(message: Message, state: FSMContext):
    """Process body measurements."""
    user_data = await state.get_data()
    measurements = {"weight": user_data.get("weight")}
    
    try:
        # Parse measurements
        text = message.text.strip()
        if text.lower() in ["пропустить", "skip", "нет"]:
            await save_progress_entry(message, state, measurements)
            return
        
        # Try to parse comma-separated values
        parts = [p.strip() for p in text.split(",")]
        if len(parts) >= 4:
            measurements["chest"] = float(parts[0])
            measurements["waist"] = float(parts[1])
            measurements["lower_abdomen"] = float(parts[2])
            measurements["glutes"] = float(parts[3])
        
        await save_progress_entry(message, state, measurements)
        
    except Exception as e:
        logger.error(f"Error parsing measurements: {e}")
        await message.answer(
            """
❌ Не удалось распознать данные.

Пожалуйста, введите в формате:
грудь, талия, низ живота, ягодицы

Например: 95, 80, 85, 100
            """
        )


async def save_progress_entry(message_or_callback, state: FSMContext, measurements: dict):
    """Save progress entry to database."""
    user_data = await state.get_data()
    user_id = message_or_callback.from_user.id if hasattr(message_or_callback, 'from_user') else message_or_callback.message.from_user.id
    
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if not client:
            text = "Клиент не найден"
            if hasattr(message_or_callback, 'answer'):
                await message_or_callback.answer(text)
            else:
                await message_or_callback.message.answer(text)
            return
        
        # Create progress entry using CRM integration
        entry_id = CRMIntegration.create_progress_entry(
            client_id=client.id,
            program_id=client.current_program_id,
            period=user_data.get("period", "before"),
            measurements=measurements
        )
        
        if entry_id:
            text = f"""
✅ Запись сохранена!

📊 Период: {user_data.get('period', 'before')}
💪 Вес: {measurements.get('weight', 'не указан')} кг

Используйте /progress для добавления новых записей.
            """
        else:
            text = "❌ Ошибка при сохранении записи. Попробуйте позже."
        
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer(text)
        else:
            await message_or_callback.message.edit_text(text)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error saving progress entry: {e}")
        text = "Произошла ошибка при сохранении. Попробуйте позже."
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer(text)
        else:
            await message_or_callback.message.answer(text)
    finally:
        db.close()

