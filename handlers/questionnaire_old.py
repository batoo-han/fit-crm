"""Questionnaire handler for client qualification."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from database.db import get_db_session
from database.models import Client, Lead
from config import TRAINING_PLAN_WOMEN, TRAINING_PLAN_MEN
from services.training_program_generator import program_generator
from services.program_formatter import ProgramFormatter
from services.pdf_generator import PDFGenerator
from services.program_storage import ProgramStorage
from aiogram.types import FSInputFile

router = Router()


class QuestionnaireStates(StatesGroup):
    """States for questionnaire flow."""
    waiting_gender = State()
    waiting_age = State()
    waiting_experience = State()
    waiting_goals = State()
    waiting_location = State()
    showing_program = State()


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Create gender selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male"),
            InlineKeyboardButton(text="👩 Женский", callback_data="gender_female"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
        ],
    ])


def get_experience_keyboard() -> InlineKeyboardMarkup:
    """Create experience level keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Новичок (0-6 месяцев)", callback_data="exp_beginner")],
        [InlineKeyboardButton(text="🟡 Средний (6-12 месяцев)", callback_data="exp_intermediate")],
        [InlineKeyboardButton(text="🔴 Опытный (1+ год)", callback_data="exp_advanced")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="questionnaire_start")],
    ])


def get_goals_keyboard() -> InlineKeyboardMarkup:
    """Create fitness goals keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 Набор мышечной массы", callback_data="goal_muscle")],
        [InlineKeyboardButton(text="🔥 Похудение", callback_data="goal_weight_loss")],
        [InlineKeyboardButton(text="🏃 Выносливость", callback_data="goal_endurance")],
        [InlineKeyboardButton(text="⚡ Общая форма", callback_data="goal_general")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="questionnaire_start")],
    ])


def get_location_keyboard() -> InlineKeyboardMarkup:
    """Create location selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Дома", callback_data="location_home"),
            InlineKeyboardButton(text="🏋️ В зале", callback_data="location_gym"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="questionnaire_start")],
    ])


@router.message(Command("program"))
async def cmd_program(message: Message, state: FSMContext):
    """Handle /program command."""
    await state.clear()
    
    text = """
🎯 Отлично! Чтобы составить персональную программу, мне нужно узнать немного о тебе.

Это займет буквально 2 минуты!

Начнем с первого вопроса:

Какой у тебя пол?
    """
    
    await message.answer(text, reply_markup=get_gender_keyboard())
    await state.set_state(QuestionnaireStates.waiting_gender)


@router.callback_query(F.data.in_(["free_program", "questionnaire_start"]))
async def start_questionnaire(callback: CallbackQuery, state: FSMContext):
    """Start questionnaire for free program."""
    await callback.message.edit_text(
        """
🎯 Отлично! Чтобы составить персональную программу, мне нужно узнать немного о тебе.

Это займет буквально 2 минуты!

Начнем с первого вопроса:

Какой у тебя пол?
        """,
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(QuestionnaireStates.waiting_gender)
    await callback.answer()


@router.callback_query(F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Process gender selection."""
    gender = callback.data.replace("gender_", "")
    gender_text = "мужской" if gender == "male" else "женский"
    
    await state.update_data(gender=gender)
    
    await callback.message.edit_text(
        f"""
✅ Пол: {gender_text}

Следующий вопрос:

Сколько тебе лет? Напиши число.
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="questionnaire_start")]
        ])
    )
    await state.set_state(QuestionnaireStates.waiting_age)
    await callback.answer()


@router.message(QuestionnaireStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    """Process age input."""
    try:
        age = int(message.text)
        if age < 10 or age > 100:
            await message.answer("Пожалуйста, укажи реальный возраст (от 10 до 100 лет)")
            return
    except ValueError:
        await message.answer("Пожалуйста, укажи возраст числом")
        return
    
    await state.update_data(age=age)
    
    # Save to database
    user_id = message.from_user.id
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client:
            client.age = age
            db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        db.close()
    
    await message.answer(
        f"""
✅ Возраст: {age} лет

Теперь уровень подготовки:

Каков твой опыт тренировок?
        """,
        reply_markup=get_experience_keyboard()
    )
    await state.set_state(QuestionnaireStates.waiting_experience)


@router.callback_query(F.data.startswith("exp_"))
async def process_experience(callback: CallbackQuery, state: FSMContext):
    """Process experience level."""
    exp = callback.data.replace("exp_", "")
    exp_map = {
        "beginner": "Новичок",
        "intermediate": "Средний",
        "advanced": "Опытный"
    }
    exp_text = exp_map[exp]
    
    await state.update_data(experience=exp)
    
    # Save to database
    user_id = callback.from_user.id
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client:
            client.experience_level = exp
            db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        db.close()
    
    await callback.message.edit_text(
        f"""
✅ Опыт: {exp_text}

Последний вопрос:

Какая у тебя цель?
        """,
        reply_markup=get_goals_keyboard()
    )
    await state.set_state(QuestionnaireStates.waiting_goals)
    await callback.answer()


@router.callback_query(F.data.startswith("goal_"))
async def process_goals(callback: CallbackQuery, state: FSMContext):
    """Process fitness goals and ask about location."""
    goal = callback.data.replace("goal_", "")
    goal_map = {
        "muscle": "Набор мышечной массы",
        "weight_loss": "Похудение",
        "endurance": "Выносливость",
        "general": "Общая форма"
    }
    goal_text = goal_map[goal]
    
    await state.update_data(goal=goal)
    
    await callback.message.edit_text(
        f"""
✅ Цель: {goal_text}

Последний вопрос:

Где ты планируешь тренироваться?
        """,
        reply_markup=get_location_keyboard()
    )
    await state.set_state(QuestionnaireStates.waiting_location)
    await callback.answer()


@router.callback_query(F.data.startswith("location_"))
async def process_location(callback: CallbackQuery, state: FSMContext):
    """Process location and generate program."""
    location = callback.data.replace("location_", "")
    location_map = {
        "home": ("дом", "🏠 Дома"),
        "gym": ("зал", "🏋️ В зале")
    }
    location_ru, location_text = location_map.get(location, ("дом", "🏠 Дома"))
    
    user_data = await state.get_data()
    goal = user_data.get("goal")
    
    await state.update_data(location=location_ru)
    
    goal_map = {
        "muscle": "Набор мышечной массы",
        "weight_loss": "Похудение",
        "endurance": "Выносливость",
        "general": "Общая форма"
    }
    goal_text = goal_map.get(goal, "Общая форма")
    
    # Save lead to database
    user_id = callback.from_user.id
    db = get_db_session()
    try:
        # Create or update lead
        lead = db.query(Lead).filter(Lead.telegram_id == user_id).first()
        if not lead:
            lead = Lead(
                telegram_id=user_id,
                source="telegram",
                status="qualified"
            )
            db.add(lead)
        
        import json
        lead.qualification_data = json.dumps({
            "gender": user_data.get("gender"),
            "age": user_data.get("age"),
            "experience": user_data.get("experience"),
            "goal": goal,
            "location": location_ru
        })
        db.commit()
        
        # Update client info
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client:
            client.gender = user_data.get("gender")
            client.age = user_data.get("age")
            client.experience_level = user_data.get("experience")
            client.fitness_goals = goal_text
            client.status = "qualified"
            db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        db.close()
    
    # Generate program from Google Sheets
    gender = user_data.get("gender")
    age = user_data.get("age")
    experience = user_data.get("experience")
    goal = goal  # Already mapped
    
    await callback.message.edit_text(
        """
⏳ Генерирую твою персональную программу тренировок...

Это займет несколько секунд.
        """
    )
    
    try:
        # Get program from Google Sheets
        program_data = await program_generator.get_program_from_sheets(
            gender=gender,
            age=age,
            experience=experience,
            goal=goal,
            location=location_ru
        )
        
        if program_data:
            # Format program using LLM
            client_name = callback.from_user.first_name or "Клиент"
            formatted_program = await ProgramFormatter.format_program(
                program_data=program_data,
                client_name=client_name
            )
            
            # Save program to database
            ProgramStorage.save_program(
                client_id=client.id,
                program_data=program_data,
                program_type="free_demo"
            )
            
            # Generate PDF
            pdf_path = PDFGenerator.generate_program_pdf(
                program_text=formatted_program,
                client_id=client.id,
                client_name=client_name
            )
            
            if pdf_path:
                # Send PDF to client
                pdf_file = FSInputFile(pdf_path)
                await callback.message.answer_document(
                    document=pdf_file,
                    caption=f"""
🎉 Твоя персональная программа тренировок готова!

✅ Цель: {goal_text}
👤 Пол: {user_data.get('gender', 'Не указано')}
📊 Опыт: {user_data.get('experience', 'Не указано')}
🎯 Возраст: {age} лет
📍 Локация: {location_text}

💡 Это базовая программа. Для достижения максимальных результатов рекомендую:

💼 Получить персональную программу:
• Индивидуальные упражнения под тебя
• План питания с расчетом КБЖУ
• Онлайн-тренировки с тренером
• Ежедневная поддержка

💰 Стоимость:
• 1 месяц: 14 999₽
• 3 месяца: 34 999₽ (экономия 9 998₽)
                    """
                )
                
                await callback.message.answer(
                    "Выбери дальнейшее действие:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Купить программу", callback_data="buy_program")],
                        [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                    ])
                )
            else:
                # Fallback: send link to Google Sheets
                training_link = TRAINING_PLAN_MEN if gender == "male" else TRAINING_PLAN_WOMEN
                await callback.message.edit_text(
                    f"""
🎉 Отлично! Вот твоя бесплатная программа тренировок:

✅ Цель: {goal_text}
👤 Пол: {user_data.get('gender', 'Не указано')}
📊 Опыт: {user_data.get('experience', 'Не указано')}

📋 Программа тренировок:
{training_link}

💡 Для получения персональной программы свяжись с тренером!
                    """,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Купить программу", callback_data="buy_program")],
                        [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                    ])
                )
        else:
            # Fallback if no program found
            training_link = TRAINING_PLAN_MEN if gender == "male" else TRAINING_PLAN_WOMEN
            await callback.message.edit_text(
                f"""
🎉 Отлично! Вот твоя бесплатная программа тренировок:

✅ Цель: {goal_text}
👤 Пол: {user_data.get('gender', 'Не указано')}
📊 Опыт: {user_data.get('experience', 'Не указано')}

📋 Программа тренировок:
{training_link}

💡 Для получения персональной программы свяжись с тренером!
                """,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Купить программу", callback_data="buy_program")],
                    [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                    [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                ])
            )
    except Exception as e:
        logger.error(f"Error generating program: {e}")
        # Fallback: send link to Google Sheets
        training_link = TRAINING_PLAN_MEN if gender == "male" else TRAINING_PLAN_WOMEN
        await callback.message.edit_text(
            f"""
🎉 Отлично! Вот твоя бесплатная программа тренировок:

✅ Цель: {goal_text}
👤 Пол: {user_data.get('gender', 'Не указано')}
📊 Опыт: {user_data.get('experience', 'Не указано')}

📋 Программа тренировок:
{training_link}

💡 Для получения персональной программы свяжись с тренером!
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Купить программу", callback_data="buy_program")],
                [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
            ])
        )
    
    await state.set_state(QuestionnaireStates.showing_program)
    await callback.answer()
