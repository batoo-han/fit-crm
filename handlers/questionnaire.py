"""New detailed questionnaire handler for client qualification."""
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
from handlers.utils import safe_callback_answer

router = Router()


class QuestionnaireStates(StatesGroup):
    """States for detailed questionnaire flow."""
    waiting_age = State()
    waiting_gender = State()
    waiting_height_weight = State()
    waiting_experience = State()
    waiting_goal = State()
    waiting_health = State()
    waiting_lifestyle = State()
    waiting_training_history = State()
    waiting_location = State()
    waiting_equipment = State()
    waiting_nutrition = State()
    generating_program = State()


def calculate_bmi(weight: float, height: float) -> tuple[float, str]:
    """Calculate BMI and return comment."""
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    
    if bmi < 18.5:
        comment = "Рекомендую программу для набора мышечной массы."
    elif bmi < 25:
        comment = "Ваш ИМТ в норме. Программа поможет укрепить тело и поддерживать форму."
    elif bmi < 30:
        comment = "План тренировок поможет скорректировать вес без стресса."
    else:
        comment = "Совместно с тренировками рекомендую скорректировать питание."
    
    return round(bmi, 1), comment


@router.message(Command("program"))
async def cmd_program(message: Message, state: FSMContext):
    """Handle /program command - start questionnaire."""
    await state.clear()
    
    # Check if already has free program
    user_id = message.from_user.id
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client and client.id:
            from handlers.start import has_free_program
            if has_free_program(client.id):
                await message.answer(
                    """
⚠️ Вы уже получили бесплатную программу тренировок!

💼 Для достижения максимальных результатов рекомендую приобрести персональную программу с:
• Индивидуальными упражнениями под тебя
• Планом питания с расчетом КБЖУ
• Онлайн-тренировками с тренером
• Ежедневной поддержкой

Используйте /my_programs чтобы посмотреть сохраненные программы.
                    """,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💼 Купить программу", callback_data="buy_program")],
                        [InlineKeyboardButton(text="📋 Мои программы", callback_data="my_programs")],
                        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                    ])
                )
                return
    except Exception as e:
        logger.error(f"Error checking free program: {e}")
    finally:
        db.close()
    
    await message.answer(
        """
🎯 Отлично! Я помогу составить персональную программу тренировок.

Для этого мне нужно узнать немного о тебе. Это займет 2-3 минуты.

Начнем с первого вопроса:

**Сколько вам полных лет?**

Это поможет подобрать безопасную нагрузку.
        """
    )
    await state.set_state(QuestionnaireStates.waiting_age)


@router.callback_query(F.data == "free_program")
async def start_free_program(callback: CallbackQuery, state: FSMContext):
    """Handle free program button - start questionnaire."""
    await state.clear()
    
    # Check if already has free program
    user_id = callback.from_user.id
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if client and client.id:
            from handlers.start import has_free_program
            if has_free_program(client.id):
                await callback.message.edit_text(
                    """
⚠️ Вы уже получили бесплатную программу тренировок!

💼 Для достижения максимальных результатов рекомендую приобрести персональную программу с:
• Индивидуальными упражнениями под тебя
• Планом питания с расчетом КБЖУ
• Онлайн-тренировками с тренером
• Ежедневной поддержкой
                    """,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💼 Купить программу", callback_data="buy_program")],
                        [InlineKeyboardButton(text="📋 Мои программы", callback_data="my_programs")],
                        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                    ])
                )
                await safe_callback_answer(callback)
                return
    except Exception as e:
        logger.error(f"Error checking free program: {e}")
    finally:
        db.close()
    
    await callback.message.edit_text(
        """
🎯 Отлично! Я помогу составить персональную программу тренировок.

Для этого мне нужно узнать немного о тебе. Это займет 2-3 минуты.

Начнем с первого вопроса:

**Сколько вам полных лет?**

Это поможет подобрать безопасную нагрузку.
        """
    )
    await state.set_state(QuestionnaireStates.waiting_age)
    await safe_callback_answer(callback)


@router.message(QuestionnaireStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    """Process age input."""
    try:
        age = int(message.text)
        
        # Validation
        if age < 14:
            await message.answer(
                """
⚠️ Важно проконсультироваться с врачом перед началом тренировок.

Для лиц младше 14 лет программа должна быть составлена специалистом.

Хотите записаться на консультацию с тренером?
                """,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
                ])
            )
            return
        elif age > 70:
            await message.answer(
                """
⚠️ Важно проконсультироваться с врачом перед началом тренировок.

Для лиц старше 70 лет программа должна быть составлена с учетом особенностей здоровья.

Хотите записаться на консультацию с тренером?
                """,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
                ])
            )
            return
        
        # Motivation
        motivation = ""
        if age > 40:
            motivation = "\n\n💪 Отличный возраст, чтобы начать! Регулярные тренировки помогут сохранить энергию и здоровье."
        elif age < 25:
            motivation = "\n\n💪 Отличный возраст для начала! Сейчас самое время заложить основы здорового образа жизни."
        
        await state.update_data(age=age)
        
        await message.answer(
            f"""
✅ Возраст: {age} лет{motivation}

Следующий вопрос:

**Укажите ваш пол для персонализации программы:**
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male")],
                [InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )
        await state.set_state(QuestionnaireStates.waiting_gender)
        
    except ValueError:
        await message.answer(
            """
❌ Пожалуйста, укажите возраст цифрами, например: 25.
            """
        )


@router.callback_query(F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Process gender selection."""
    gender_code = callback.data.replace("gender_", "")
    gender_map = {
        "male": ("мужской", "👨 Мужской"),
        "female": ("женский", "👩 Женский")
    }
    gender_ru, gender_text = gender_map.get(gender_code, ("мужской", "👨 Мужской"))
    
    await state.update_data(gender=gender_code, gender_ru=gender_ru)
    
    await callback.message.edit_text(
        f"""
✅ Пол: {gender_text}

Следующий вопрос:

**Укажите ваш рост (в см) и вес (в кг).**

Например: 175 см, 68 кг

Или в одну строку: 175 68
        """
    )
    await state.set_state(QuestionnaireStates.waiting_height_weight)
    await callback.answer()


@router.message(QuestionnaireStates.waiting_height_weight)
async def process_height_weight(message: Message, state: FSMContext):
    """Process height and weight input."""
    try:
        text = message.text.strip()
        
        # Parse different formats
        # Try "175 см, 68 кг" or "175, 68" or "175 68"
        import re
        numbers = re.findall(r'\d+', text)
        
        if len(numbers) < 2:
            await message.answer(
                """
❌ Пожалуйста, укажите рост и вес.

Формат: 175 см, 68 кг
Или просто: 175 68
                """
            )
            return
        
        height = int(numbers[0])
        weight = int(numbers[1])
        
        # Validation
        if height < 100 or height > 250:
            await message.answer(
                """
❌ Проверьте, пожалуйста, данные. Рост должен быть в пределах 100–250 см.

Укажите рост еще раз:
                """
            )
            return
        
        if weight < 30 or weight > 300:
            await message.answer(
                """
❌ Проверьте, пожалуйста, данные. Вес должен быть в пределах 30–300 кг.

Укажите вес еще раз:
                """
            )
            return
        
        # Calculate BMI
        bmi, bmi_comment = calculate_bmi(weight, height)
        
        await state.update_data(height=height, weight=weight, bmi=bmi)
        
        await message.answer(
            f"""
✅ Рост: {height} см
✅ Вес: {weight} кг
📊 ИМТ: {bmi}

💡 {bmi_comment}

Следующий вопрос:

**Как часто вы тренируетесь?**

Выберите ваш уровень подготовки:
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Новичок (занимаюсь редко или никогда)", callback_data="exp_beginner")],
                [InlineKeyboardButton(text="🟡 Средний уровень (1–3 раза в неделю)", callback_data="exp_intermediate")],
                [InlineKeyboardButton(text="🔴 Продвинутый (4+ раза в неделю)", callback_data="exp_advanced")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )
        await state.set_state(QuestionnaireStates.waiting_experience)
        
    except Exception as e:
        logger.error(f"Error processing height/weight: {e}")
        await message.answer(
            """
❌ Не удалось распознать данные. Пожалуйста, укажите в формате:
175 см, 68 кг
            """
        )


@router.callback_query(F.data.startswith("exp_"))
async def process_experience(callback: CallbackQuery, state: FSMContext):
    """Process experience level."""
    exp_code = callback.data.replace("exp_", "")
    exp_map = {
        "beginner": ("новичок", "🟢 Новичок", "Каждый профессионал начинал с нуля — вы на верном пути!"),
        "intermediate": ("средний", "🟡 Средний уровень", "Отличный уровень! Готовы к прогрессу."),
        "advanced": ("продвинутый", "🔴 Продвинутый", "Вижу, вы серьёзно настроены! Добавлю в программу интенсивные упражнения.")
    }
    exp_ru, exp_text, motivation = exp_map[exp_code]
    
    await state.update_data(experience=exp_code, experience_ru=exp_ru)
    
    await callback.message.edit_text(
        f"""
✅ Уровень подготовки: {exp_text}

💪 {motivation}

Следующий вопрос:

**Какую главную цель вы преследуете?**

Выберите вашу цель:
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Похудение", callback_data="goal_weight_loss")],
            [InlineKeyboardButton(text="💪 Набор массы", callback_data="goal_muscle")],
            [InlineKeyboardButton(text="⚡ Поддержание формы", callback_data="goal_maintenance")],
            [InlineKeyboardButton(text="🏃 Развитие выносливости", callback_data="goal_endurance")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ])
    )
    await state.set_state(QuestionnaireStates.waiting_goal)
    await callback.answer()


@router.callback_query(F.data.startswith("goal_"))
async def process_goal(callback: CallbackQuery, state: FSMContext):
    """Process fitness goal."""
    goal_code = callback.data.replace("goal_", "")
    goal_map = {
        "weight_loss": ("похудение", "🔥 Похудение", "Отличный выбор! Совместим кардио и силовые тренировки для максимального эффекта."),
        "muscle": ("набор массы", "💪 Набор массы", "Сфокусируемся на базовых упражнениях с прогрессией нагрузок."),
        "maintenance": ("поддержание формы", "⚡ Поддержание формы", "Отличная цель! Поддержим форму и улучшим здоровье."),
        "endurance": ("выносливость", "🏃 Развитие выносливости", "Отличный выбор для повышения выносливости и энергии!")
    }
    goal_ru, goal_text, motivation = goal_map.get(goal_code, ("общая форма", "⚡ Общая форма", ""))
    
    await state.update_data(goal=goal_code, goal_ru=goal_ru)
    
    await callback.message.edit_text(
        f"""
✅ Цель: {goal_text}

💪 {motivation}

Следующий вопрос:

**Есть ли у вас хронические заболевания, травмы или другие ограничения?**

Например, проблемы с суставами, сердцем и т.д.

Если ограничений нет, напишите "нет" или "нет ограничений".
        """
    )
    await state.set_state(QuestionnaireStates.waiting_health)
    await callback.answer()


@router.message(QuestionnaireStates.waiting_health)
async def process_health(message: Message, state: FSMContext):
    """Process health restrictions."""
    health_text = message.text.lower().strip()
    
    # Check for serious conditions
    serious_conditions = ["сердце", "сердечно", "сосуд", "инфаркт", "инсульт", "гипертония", "гипертензия"]
    has_serious = any(condition in health_text for condition in serious_conditions)
    
    if has_serious:
        await message.answer(
            """
⚠️ Для вашей безопасности советую проконсультироваться с врачом перед началом тренировок.

Рекомендую:
1. Проконсультироваться с врачом
2. Получить разрешение на тренировки
3. После этого связаться со мной для составления программы

Хотите записаться на консультацию с тренером?
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )
        await state.set_state(QuestionnaireStates.waiting_health)
        return
    
    if health_text in ["нет", "нет ограничений", "ограничений нет", "нет проблем"]:
        motivation = "Здорово, что вы следите за собой! Это упростит подбор упражнений."
    else:
        motivation = "Спасибо за информацию! Учту ваши особенности при составлении программы."
    
    await state.update_data(health_restrictions=message.text)
    
    await message.answer(
        f"""
✅ Спасибо за информацию!

💪 {motivation}

Следующий вопрос:

**Опишите ваш образ жизни:**

Выберите вариант:
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🪑 Сидячий (офисная работа, мало активности)", callback_data="lifestyle_sedentary")],
            [InlineKeyboardButton(text="🚶 Умеренная активность (прогулки, домашние дела)", callback_data="lifestyle_moderate")],
            [InlineKeyboardButton(text="🏃 Высокая активность (физическая работа, спорт)", callback_data="lifestyle_active")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ])
    )
    await state.set_state(QuestionnaireStates.waiting_lifestyle)


@router.callback_query(F.data.startswith("lifestyle_"))
async def process_lifestyle(callback: CallbackQuery, state: FSMContext):
    """Process lifestyle."""
    lifestyle_code = callback.data.replace("lifestyle_", "")
    lifestyle_map = {
        "sedentary": ("сидячий", "🪑 Сидячий", "Начнем с малого — даже 20 минут в день дадут результат!"),
        "moderate": ("умеренная активность", "🚶 Умеренная активность", "Отлично! Добавим структурированные тренировки."),
        "active": ("высокая активность", "🏃 Высокая активность", "Отлично! Учту вашу активность при составлении программы.")
    }
    lifestyle_ru, lifestyle_text, motivation = lifestyle_map[lifestyle_code]
    
    await state.update_data(lifestyle=lifestyle_code, lifestyle_ru=lifestyle_ru)
    
    await callback.message.edit_text(
        f"""
✅ Образ жизни: {lifestyle_text}

💪 {motivation}

Следующий вопрос:

**Занимались ли вы раньше спортом или фитнесом?**

Если да, опишите кратко. Если нет, напишите "нет" или "не занимался".
        """
    )
    await state.set_state(QuestionnaireStates.waiting_training_history)
    await callback.answer()


@router.message(QuestionnaireStates.waiting_training_history)
async def process_training_history(message: Message, state: FSMContext):
    """Process training history."""
    history_text = message.text.lower().strip()
    
    # Skip if unclear
    if history_text in ["не помню", "не знаю", "не помню", "не знаю точно"]:
        await state.update_data(training_history="не указано")
    else:
        await state.update_data(training_history=message.text)
    
    await message.answer(
        """
✅ Спасибо за информацию!

Следующий вопрос:

**Где вы планируете тренироваться?**

Выберите вариант:
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Дома", callback_data="location_home")],
            [InlineKeyboardButton(text="🏋️ В зале", callback_data="location_gym")],
            [InlineKeyboardButton(text="🌳 На улице", callback_data="location_outdoor")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ])
    )
    await state.set_state(QuestionnaireStates.waiting_location)


@router.callback_query(F.data.startswith("location_"))
async def process_location(callback: CallbackQuery, state: FSMContext):
    """Process location."""
    location_code = callback.data.replace("location_", "")
    location_map = {
        "home": ("дом", "🏠 Дома", "Составлю программу, для которой не нужно сложное оборудование!"),
        "gym": ("зал", "🏋️ В зале", "Отлично! В зале можно использовать все оборудование для максимального эффекта."),
        "outdoor": ("улица", "🌳 На улице", "Отлично! Тренировки на свежем воздухе — это здорово!")
    }
    location_ru, location_text, motivation = location_map[location_code]
    
    await state.update_data(location=location_code, location_ru=location_ru)
    
    # Skip equipment question if gym
    if location_code == "gym":
        await state.update_data(equipment="полный набор оборудования в зале")
        await callback.message.edit_text(
            f"""
✅ Место тренировок: {location_text}

💪 {motivation}

Следующий вопрос:

**Придерживаетесь ли вы особой диеты?**

Например, вегетарианство, низкоуглеводное питание, аллергии.

Если нет, напишите "нет" или "нет ограничений".
            """
        )
        await state.set_state(QuestionnaireStates.waiting_nutrition)
    else:
        await callback.message.edit_text(
            f"""
✅ Место тренировок: {location_text}

💪 {motivation}

Следующий вопрос:

**Есть ли у вас гантели, эспандер, турник или другое оборудование?**

Перечислите, что есть. Если нет оборудования, напишите "нет".
            """
        )
        await state.set_state(QuestionnaireStates.waiting_equipment)
    
    await callback.answer()


@router.message(QuestionnaireStates.waiting_equipment)
async def process_equipment(message: Message, state: FSMContext):
    """Process equipment."""
    equipment_text = message.text.lower().strip()
    
    if equipment_text in ["нет", "нет оборудования", "ничего нет"]:
        equipment = "нет оборудования"
        motivation = "Хорошо, предложу упражнения с весом тела."
    else:
        equipment = message.text
        motivation = "Отлично! Учту ваше оборудование при составлении программы."
    
    await state.update_data(equipment=equipment)
    
    await message.answer(
        f"""
✅ Спасибо за информацию!

💪 {motivation}

Последний вопрос:

**Придерживаетесь ли вы особой диеты?**

Например, вегетарианство, низкоуглеводное питание, аллергии.

Если нет, напишите "нет" или "нет ограничений".
        """
    )
    await state.set_state(QuestionnaireStates.waiting_nutrition)


@router.message(QuestionnaireStates.waiting_nutrition)
async def process_nutrition(message: Message, state: FSMContext):
    """Process nutrition and finish questionnaire."""
    nutrition_text = message.text.lower().strip()
    
    if nutrition_text in ["нет", "нет ограничений", "ограничений нет"]:
        nutrition = "нет ограничений"
        motivation = "Рекомендую добавить в рацион больше белка — это усилит эффект от тренировок!"
    else:
        nutrition = message.text
        motivation = "Спасибо за информацию! Учту ваши предпочтения при рекомендациях по питанию."
    
    await state.update_data(nutrition=nutrition)
    
    user_data = await state.get_data()
    
    # Save all data to database
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    db = get_db_session()
    try:
        # Create or update client
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if not client:
            client = Client(
                telegram_id=user_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name
            )
            db.add(client)
        
        # Update all client data
        client.age = user_data.get("age")
        client.gender = user_data.get("gender_ru", "мужской")
        client.height = user_data.get("height")
        client.weight = user_data.get("weight")
        client.bmi = user_data.get("bmi")
        client.experience_level = user_data.get("experience_ru", "новичок")
        client.fitness_goals = user_data.get("goal_ru", "общая форма")
        client.health_restrictions = user_data.get("health_restrictions")
        client.lifestyle = user_data.get("lifestyle_ru")
        client.training_history = user_data.get("training_history")
        client.location = user_data.get("location_ru", "дом")
        client.equipment = user_data.get("equipment")
        client.nutrition = user_data.get("nutrition")
        client.status = "qualified"
        
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
            "age": user_data.get("age"),
            "gender": user_data.get("gender"),
            "gender_ru": user_data.get("gender_ru"),
            "height": user_data.get("height"),
            "weight": user_data.get("weight"),
            "bmi": user_data.get("bmi"),
            "experience": user_data.get("experience"),
            "experience_ru": user_data.get("experience_ru"),
            "goal": user_data.get("goal"),
            "goal_ru": user_data.get("goal_ru"),
            "health_restrictions": user_data.get("health_restrictions"),
            "lifestyle": user_data.get("lifestyle"),
            "lifestyle_ru": user_data.get("lifestyle_ru"),
            "training_history": user_data.get("training_history"),
            "location": user_data.get("location"),
            "location_ru": user_data.get("location_ru"),
            "equipment": user_data.get("equipment"),
            "nutrition": user_data.get("nutrition")
        }, ensure_ascii=False)
        
        db.commit()
        logger.info(f"Client {client.id} completed questionnaire")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Generate program
    await message.answer(
        f"""
✅ Спасибо за информацию!

💪 {motivation}

⏳ Генерирую твою персональную программу тренировок...

Это займет несколько секунд.
        """
    )
    
    await state.set_state(QuestionnaireStates.generating_program)
    
    try:
        # Get program from Google Sheets
        # Map goal codes to match generator expectations
        goal_map = {
            "weight_loss": "weight_loss",
            "muscle": "muscle",
            "maintenance": "general",
            "endurance": "endurance"
        }
        goal_code = goal_map.get(user_data.get("goal"), "general")
        
        program_data = await program_generator.get_program_from_sheets(
            gender=user_data.get("gender"),  # "male" or "female"
            age=user_data.get("age"),
            experience=user_data.get("experience"),  # "beginner", "intermediate", "advanced"
            goal=goal_code,
            location=user_data.get("location_ru", "дом")
        )
        
        if program_data:
            # Format program using LLM
            client_name = first_name or "Клиент"
            formatted_program = await ProgramFormatter.format_program(
                program_data=program_data,
                client_name=client_name
            )
            
            # Save program to database
            db = get_db_session()
            try:
                client = db.query(Client).filter(Client.telegram_id == user_id).first()
                if client:
                    ProgramStorage.save_program(
                        client_id=client.id,
                        program_data=program_data,
                        program_type="free_demo",
                        formatted_program=formatted_program
                    )
                    
                    # Move client to "Консультация" stage after completing questionnaire
                    try:
                        from services.crm_integration import CRMIntegration
                        CRMIntegration.move_client_to_qualified_stage(client_id=client.id)
                    except Exception as e:
                        logger.error(f"Error moving client to qualified stage: {e}")
            except Exception as e:
                logger.error(f"Error saving program: {e}")
            finally:
                db.close()
            
            # Generate PDF
            pdf_path = PDFGenerator.generate_program_pdf(
                program_text=formatted_program,
                client_id=client.id if client else user_id,
                client_name=client_name
            )
            
            if pdf_path:
                # Send PDF to client
                pdf_file = FSInputFile(pdf_path)
                await message.answer_document(
                    document=pdf_file,
                    caption=f"""
🎉 Твоя персональная программа тренировок готова!

📋 Программа составлена на основе твоих данных:
• Возраст: {user_data.get('age')} лет
• Пол: {user_data.get('gender_ru', 'мужской')}
• Цель: {user_data.get('goal_ru', 'общая форма')}
• Опыт: {user_data.get('experience_ru', 'новичок')}
• Место тренировок: {user_data.get('location_ru', 'дом')}

💡 Это базовая программа. Для достижения максимальных результатов рекомендую:

💼 Получить персональную программу с:
• Индивидуальными упражнениями под тебя
• Планом питания с расчетом КБЖУ
• Онлайн-тренировками с тренером
• Ежедневной поддержкой

💰 Стоимость:
• 1 месяц: 14 999₽
• 3 месяца: 34 999₽ (экономия 9 998₽)
                    """
                )
                
                await message.answer(
                    "Выбери дальнейшее действие:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Купить программу", callback_data="buy_program")],
                        [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                    ])
                )
            else:
                await message.answer(
                    """
❌ Не удалось создать PDF файл. 

Пожалуйста, свяжись с тренером для получения программы:
                    """,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                    ])
                )
        else:
            await message.answer(
                """
❌ Не удалось найти подходящую программу в базе.

Пожалуйста, свяжись с тренером для получения персональной программы:
                """,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                    [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
                ])
            )
    except Exception as e:
        logger.error(f"Error generating program: {e}")
        await message.answer(
            """
❌ Произошла ошибка при генерации программы.

Пожалуйста, свяжись с тренером:
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
            ])
        )
