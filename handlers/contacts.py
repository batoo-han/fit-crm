"""Contacts and info handlers."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import TRAINER_NAME, TRAINER_TELEGRAM, TRAINER_PHONE

router = Router()


@router.message(F.text == "/contacts")
async def cmd_contacts(message: Message):
    """Handle /contacts command."""
    contacts_text = f"""
👋 Контакты тренера {TRAINER_NAME}

📞 WhatsApp: {TRAINER_PHONE}

📍 Адрес:
просп. Пацаева, 7, корп. 11
г. Долгопрудный, Московская область

🏋️ Обо мне:
• Личный тренировочный стаж - 7 лет
• Опыт работы тренером - 3 года
• Работаю в фитнес-клубе «С.С.С.Р.» г. Долгопрудный
• Индивидуальный подход к каждому клиенту
• Безопасная техника выполнения упражнений

Выбери удобный способ связи 👇
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📞 WhatsApp", url=f"https://wa.me/{TRAINER_PHONE.replace('+', '')}"),
        ],
        [
            InlineKeyboardButton(text="📍 Яндекс.Карты", url="https://yandex.ru/maps/-/CLvZUNnO"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu"),
        ],
    ])
    
    await message.answer(contacts_text, reply_markup=keyboard)


@router.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    """Show trainer contacts."""
    contacts_text = f"""
👋 Контакты тренера {TRAINER_NAME}

📞 WhatsApp: {TRAINER_PHONE}

📍 Адрес:
просп. Пацаева, 7, корп. 11
г. Долгопрудный, Московская область

🏋️ Обо мне:
• Личный тренировочный стаж - 7 лет
• Опыт работы тренером - 3 года
• Работаю в фитнес-клубе «С.С.С.Р.» г. Долгопрудный
• Индивидуальный подход к каждому клиенту
• Безопасная техника выполнения упражнений

Выбери удобный способ связи 👇
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📞 WhatsApp", url=f"https://wa.me/{TRAINER_PHONE.replace('+', '')}"),
        ],
        [
            InlineKeyboardButton(text="📍 Яндекс.Карты", url="https://yandex.ru/maps/-/CLvZUNnO"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu"),
        ],
    ])
    
    await callback.message.edit_text(
        contacts_text,
        reply_markup=keyboard
    )
    await callback.answer()