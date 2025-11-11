"""FAQ handlers with database integration."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db_session
from database.models_crm import FAQ
from services.faq_service import FAQService
from loguru import logger

router = Router()


def get_faq_keyboard(db_session=None) -> InlineKeyboardMarkup:
    """Create FAQ keyboard from database."""
    db = db_session or get_db_session()
    try:
        # Get top 5 FAQ items by priority
        faq_items = FAQService.get_all_faq(db, is_active=True)[:5]
        
        buttons = []
        for faq in faq_items:
            # Truncate question for button text
            button_text = faq.question[:40] + "..." if len(faq.question) > 40 else faq.question
            buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"faq_{faq.id}")])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    except Exception as e:
        logger.error(f"Error getting FAQ keyboard: {e}")
        # Fallback to default keyboard
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Цены", callback_data="faq_price")],
            [InlineKeyboardButton(text="⚡ Результаты", callback_data="faq_results")],
            [InlineKeyboardButton(text="🎯 Опыт", callback_data="faq_experience")],
            [InlineKeyboardButton(text="🏥 Здоровье", callback_data="faq_health")],
            [InlineKeyboardButton(text="💻 Онлайн", callback_data="faq_online")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ])
    finally:
        if not db_session:
            db.close()


@router.message(F.text == "/faq")
async def cmd_faq(message: Message):
    """Handle /faq command."""
    db = get_db_session()
    try:
        faq_text = """
❓ Часто задаваемые вопросы

Выбери интересующий вопрос:
        """
        
        await message.answer(
            faq_text,
            reply_markup=get_faq_keyboard(db)
        )
    except Exception as e:
        logger.error(f"Error showing FAQ: {e}")
        await message.answer("Произошла ошибка при загрузке FAQ. Попробуйте позже.")
    finally:
        db.close()


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery):
    """Show FAQ menu."""
    db = get_db_session()
    try:
        faq_text = """
❓ Часто задаваемые вопросы

Выбери интересующий вопрос:
        """
        
        await callback.message.edit_text(
            faq_text,
            reply_markup=get_faq_keyboard(db)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing FAQ: {e}")
        await callback.answer("Ошибка при загрузке FAQ", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("faq_"))
async def show_faq_answer(callback: CallbackQuery):
    """Show FAQ answer by ID."""
    db = get_db_session()
    try:
        # Extract FAQ ID from callback data
        faq_id_str = callback.data.replace("faq_", "")
        
        # Handle legacy callback data
        if faq_id_str in ["price", "results", "experience", "health", "online"]:
            # Use legacy handlers for backward compatibility
            if faq_id_str == "price":
                await faq_price_legacy(callback)
            elif faq_id_str == "results":
                await faq_results_legacy(callback)
            elif faq_id_str == "experience":
                await faq_experience_legacy(callback)
            elif faq_id_str == "health":
                await faq_health_legacy(callback)
            elif faq_id_str == "online":
                await faq_online_legacy(callback)
            return
        
        faq_id = int(faq_id_str)
        faq = FAQService.get_faq_by_id(db, faq_id)
        
        if not faq:
            await callback.answer("Вопрос не найден", show_alert=True)
            return
        
        # Increment use count
        faq.use_count += 1
        db.commit()
        
        await callback.message.edit_text(
            faq.answer,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")],
            ]),
            parse_mode="Markdown"
        )
        await callback.answer()
    except ValueError:
        await callback.answer("Неверный ID вопроса", show_alert=True)
    except Exception as e:
        logger.error(f"Error showing FAQ answer: {e}")
        await callback.answer("Ошибка при загрузке ответа", show_alert=True)
    finally:
        db.close()


# Legacy handlers for backward compatibility
async def faq_price_legacy(callback: CallbackQuery):
    """Answer about pricing (legacy)."""
    answer = """
💰 **Сколько стоят ваши услуги?**

Стоимость зависит от выбранного формата:

📞 **Онлайн-консультация (1 час)** - 1 490₽

💼 **Персональное онлайн-сопровождение (1 месяц)** - 14 999₽
Включает: программу тренировок, питание, 3 онлайн-тренировки, ежедневную поддержку

🏆 **Персональное онлайн-сопровождение (3 месяца)** - 34 999₽
Экономия 9 998₽! Расширенная программа с 9 онлайн-тренировками

💡 Также доступны офлайн-тренировки в зале в Долгопрудном
    """
    
    await callback.message.edit_text(
        answer,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Узнать цены", callback_data="prices")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def faq_results_legacy(callback: CallbackQuery):
    """Answer about results (legacy)."""
    answer = """
⚡ **Как быстро я увижу результаты?**

Первые заметные изменения:
• Через 2-3 недели - улучшение самочувствия и энергии
• Через 4-6 недель - видимые изменения в фигуре
• Через 2-3 месяца - значительный прогресс

🎯 Скорость зависит от:
• Начальной физической формы
• Соблюдения программы тренировок и питания
• Регулярности занятий
• Индивидуальных особенностей организма

При соблюдении всех рекомендаций результаты гарантированы! 💪
    """
    
    await callback.message.edit_text(
        answer,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Получить программу", callback_data="free_program")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def faq_experience_legacy(callback: CallbackQuery):
    """Answer about required experience (legacy)."""
    answer = """
🎯 **Нужен ли мне опыт тренировок?**

Нет, опыт не обязателен! 

Я работаю с:
🟢 Новичками - помогаю начать с нуля
🟡 Средним уровнем - помогаю прогрессировать
🔴 Опытными - помогаю достичь новых целей

✅ Моя задача:
• Научить правильной технике выполнения упражнений
• Составить программу под твой уровень
• Помочь избежать травм
• Поддержать на каждом этапе

Главное - желание изменить себя! 💪
    """
    
    await callback.message.edit_text(
        answer,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Получить программу", callback_data="free_program")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def faq_health_legacy(callback: CallbackQuery):
    """Answer about health issues (legacy)."""
    answer = """
🏥 **Можно ли тренироваться при проблемах со здоровьем?**

✅ **Да, но с обязательной консультацией врача!**

Перед началом тренировок, особенно при наличии:
• Хронических заболеваний
• Травм (прошлых или текущих)
• Беременности
• Сердечно-сосудистых проблем

Необходимо проконсультироваться с врачом.

✅ Я учту все твои особенности при составлении программы:
• Адаптирую упражнения под твои возможности
• Скорректирую интенсивность
• Подберу безопасные альтернативы

Здоровье превыше всего! 🏥
    """
    
    await callback.message.edit_text(
        answer,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


async def faq_online_legacy(callback: CallbackQuery):
    """Answer about online coaching (legacy)."""
    answer = """
💻 **Как работает онлайн-сопровождение?**

Формат включает:

📋 **Индивидуальный план тренировок**
Персональная программа под твои цели

🥗 **План питания с расчетом КБЖУ**
Персональные рекомендации по питанию

💪 **Онлайн-тренировки (3 или 9 сессий)**
Тренировки через Zoom/WhatsApp с контролем техники

📱 **Ежедневная поддержка**
Связь через Telegram/WhatsApp для:
• Отчетности по тренировкам и питанию
• Корректировки программы
• Ответов на вопросы
• Мотивации

🎥 **Видео-демонстрации**
Все упражнения показаны в видеоформате

✅ **Гибкий график** - тренируйся когда удобно!
    """
    
    await callback.message.edit_text(
        answer,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 Посмотреть тарифы", callback_data="prices")],
            [InlineKeyboardButton(text="⬅️ Назад к FAQ", callback_data="faq")],
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()