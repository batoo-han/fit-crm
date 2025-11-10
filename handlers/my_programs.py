"""Handler for viewing client's training programs."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger
from database.db import get_db_session
from database.models import Client
from services.program_storage import ProgramStorage
from services.pdf_generator import PDFGenerator
from aiogram.types import FSInputFile
import os


router = Router()


async def show_my_programs(user_id: int, message_or_callback):
    """Show client's training programs (common logic)."""
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if not client:
            text = "Вы еще не проходили опросник. Используйте /program для получения программы."
            if hasattr(message_or_callback, 'edit_text'):
                await message_or_callback.edit_text(text)
            else:
                await message_or_callback.answer(text)
            return
        
        # Get all programs
        programs = ProgramStorage.get_client_programs(client.id)
        
        if not programs:
            text = """
📋 У вас пока нет сохраненных программ тренировок.

🎯 Используйте /program чтобы получить персональную программу!
            """
            if hasattr(message_or_callback, 'edit_text'):
                await message_or_callback.edit_text(text)
            else:
                await message_or_callback.answer(text)
            return
        
        # Show programs list
        programs_text = f"""
📋 Ваши программы тренировок:

Всего программ: {len(programs)}

"""
        
        for i, program in enumerate(programs[:5], 1):  # Show first 5
            program_type = program['type']
            type_map = {
                "free_demo": "Бесплатная демо",
                "paid_monthly": "Персональная (1 месяц)",
                "paid_3month": "Персональная (3 месяца)"
            }
            type_text = type_map.get(program_type, "Программа")
            
            created_at = program.get('created_at', '')[:10]  # Date only
            status = "✅ Завершена" if program.get('is_completed') else "🔄 Активна"
            
            programs_text += f"{i}. {type_text} - {created_at} - {status}\n"
        
        if len(programs) > 5:
            programs_text += f"\n... и еще {len(programs) - 5} программ"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Скачать последнюю программу", callback_data="download_last_program")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
        ])
        
        if hasattr(message_or_callback, 'edit_text'):
            await message_or_callback.edit_text(programs_text, reply_markup=keyboard)
        else:
            await message_or_callback.answer(programs_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error getting programs: {e}")
        text = "Ошибка при получении программ. Попробуйте позже."
        if hasattr(message_or_callback, 'edit_text'):
            await message_or_callback.edit_text(text)
        else:
            await message_or_callback.answer(text)
    finally:
        db.close()


@router.message(Command("my_programs"))
async def cmd_my_programs(message: Message):
    """Show client's training programs."""
    await show_my_programs(message.from_user.id, message)


@router.callback_query(F.data == "my_programs")
async def callback_my_programs(callback: CallbackQuery):
    """Show client's training programs via callback."""
    from handlers.utils import safe_callback_answer
    
    await show_my_programs(callback.from_user.id, callback)
    await safe_callback_answer(callback)


@router.callback_query(F.data == "download_last_program")
async def download_last_program(callback: CallbackQuery):
    """Download last program PDF."""
    user_id = callback.from_user.id
    
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return
        
        programs = ProgramStorage.get_client_programs(client.id)
        if not programs:
            await callback.answer("У вас нет программ", show_alert=True)
            return
        
        # Find last PDF
        last_program = programs[0]
        program_id = last_program['id']
        
        # Look for PDF file
        pdf_dir = "data/programs"
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.startswith(f"program_{client.id}_")]
            if pdf_files:
                # Get most recent
                pdf_files.sort(reverse=True)
                pdf_path = os.path.join(pdf_dir, pdf_files[0])
                
                pdf_file = FSInputFile(pdf_path)
                await callback.message.answer_document(
                    document=pdf_file,
                    caption="📋 Ваша последняя программа тренировок"
                )
                await callback.answer("Программа отправлена!")
                return
        
        await callback.answer("PDF файл не найден", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error downloading program: {e}")
        await callback.answer("Ошибка при загрузке программы", show_alert=True)
    finally:
        if db:
            db.close()
