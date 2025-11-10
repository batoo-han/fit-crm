"""FAQ handlers."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


def get_faq_keyboard() -> InlineKeyboardMarkup:
    """Create FAQ keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Сколько стоят услуги?", callback_data="faq_price")],
        [InlineKeyboardButton(text="⚡ Как быстро появятся результаты?", callback_data="faq_results")],
        [InlineKeyboardButton(text="🎯 Нужен ли опыт тренировок?", callback_data="faq_experience")],
        [InlineKeyboardButton(text="🏥 Можно ли тренироваться при проблемах со здоровьем?", callback_data="faq_health")],
        [InlineKeyboardButton(text="💻 Как работает онлайн-сопровождение?", callback_data="faq_online")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


@router.message(F.text == "/faq")
async def cmd_faq(message: Message):
    """Handle /faq command."""
    faq_text = """
❓ Часто задаваемые вопросы

Выбери интересующий вопрос:
    """
    
    await message.answer(
        faq_text,
        reply_markup=get_faq_keyboard()
    )


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery):
    """Show FAQ menu."""
    faq_text = """
❓ Часто задаваемые вопросы

Выбери интересующий вопрос:
    """
    
    await callback.message.edit_text(
        faq_text,
        reply_markup=get_faq_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "faq_price")
async def faq_price(callback: CallbackQuery):
    """Answer about pricing."""
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


@router.callback_query(F.data == "faq_results")
async def faq_results(callback: CallbackQuery):
    """Answer about results."""
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


@router.callback_query(F.data == "faq_experience")
async def faq_experience(callback: CallbackQuery):
    """Answer about required experience."""
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


@router.callback_query(F.data == "faq_health")
async def faq_health(callback: CallbackQuery):
    """Answer about health issues."""
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


@router.callback_query(F.data == "faq_online")
async def faq_online(callback: CallbackQuery):
    """Answer about online coaching."""
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