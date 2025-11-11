"""Personalized recommendations handler for Telegram bot."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger
from database.db import get_db_session
from database.models import Client
from services.recommendation_service import RecommendationService
from services.sales_scenario_service import SalesScenarioService

router = Router()


def get_recommendations_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for recommendations follow-up."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить программу", callback_data="buy_program")],
        [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
        [InlineKeyboardButton(text="📋 Мои программы", callback_data="my_programs")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
    ])


@router.message(Command("recommend"))
async def cmd_recommend(message: Message):
    """Generate and show personalized recommendations for the client."""
    user_id = message.from_user.id
    db = get_db_session()
    try:
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        if not client:
            await message.answer("Сначала запустите бота и заполните данные. Используйте /start и /program")
            return

        await message.answer("⏳ Готовлю персональные рекомендации...")

        # Program recommendation
        program_rec = await RecommendationService.get_program_recommendation(db, client)
        text_parts = []
        if program_rec and program_rec.get("message"):
            text_parts.append(f"🎯 Рекомендация по программе:\n\n{program_rec['message']}")
            if program_rec.get("reasoning"):
                text_parts.append(f"\nℹ️ Основание: {program_rec['reasoning']}")

        # Sales scenarios (best matching)
        scenarios = await SalesScenarioService.get_recommendations(db, client)
        if scenarios:
            best = scenarios[0]
            text_parts.append(f"\n💡 Персональное предложение:\n\n{best['message']}")

        # Training tips
        tips = await RecommendationService.get_training_tips(db, client)
        if tips:
            text_parts.append(f"\n🏋️ Советы по тренировкам:\n\n{tips}")

        # Nutrition
        nutrition = await RecommendationService.get_nutrition_recommendations(db, client)
        if nutrition:
            text_parts.append(f"\n🥗 Рекомендации по питанию:\n\n{nutrition}")

        if not text_parts:
            await message.answer("Пока нет достаточных данных для рекомендаций. Заполните анкету через /program.")
            return

        full_text = "\n\n".join(text_parts)
        await message.answer(full_text, reply_markup=get_recommendations_keyboard())
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        await message.answer("Произошла ошибка при подготовке рекомендаций. Попробуйте позже.")
    finally:
        db.close()


@router.callback_query(F.data == "recommendations")
async def cb_recommendations(callback: CallbackQuery):
    """Alias to generate recommendations via callback button."""
    await cmd_recommend(callback.message)
    try:
        await callback.answer()
    except Exception:
        pass

"""Recommendations handler for personalized recommendations."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database.db import get_db_session
from database.models import Client
from services.recommendation_service import RecommendationService
from services.sales_scenario_service import SalesScenarioService
from loguru import logger

router = Router()


@router.message(Command("recommendations"))
async def cmd_recommendations(message: Message):
    """Handle /recommendations command - show personalized recommendations."""
    db = get_db_session()
    try:
        user_id = message.from_user.id
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        
        if not client:
            await message.answer("Сначала пройдите опросник /program для получения рекомендаций")
            return
        
        # Get personalized recommendations
        recommendations = await SalesScenarioService.get_recommendations(db, client)
        
        if not recommendations:
            await message.answer("На данный момент нет персонализированных рекомендаций. Пройдите опросник /program для получения рекомендаций")
            return
        
        # Send top recommendation
        top_recommendation = recommendations[0]
        await message.answer(
            top_recommendation["message"],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💼 Купить программу", callback_data="buy_program")],
                [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
            ])
        )
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        await message.answer("Произошла ошибка при получении рекомендаций. Попробуйте позже.")
    finally:
        db.close()


@router.callback_query(F.data == "get_recommendations")
async def get_recommendations(callback: CallbackQuery):
    """Get personalized recommendations for client."""
    db = get_db_session()
    try:
        user_id = callback.from_user.id
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        
        if not client:
            await callback.answer("Сначала пройдите опросник /program", show_alert=True)
            return
        
        # Get personalized recommendations
        recommendations = await SalesScenarioService.get_recommendations(db, client)
        
        if not recommendations:
            await callback.answer("Нет персонализированных рекомендаций", show_alert=True)
            return
        
        # Send top recommendation
        top_recommendation = recommendations[0]
        await callback.message.answer(
            top_recommendation["message"],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💼 Купить программу", callback_data="buy_program")],
                [InlineKeyboardButton(text="📞 Связаться с тренером", callback_data="contacts")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_menu")],
            ])
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        await callback.answer("Ошибка при получении рекомендаций", show_alert=True)
    finally:
        db.close()


@router.message(Command("nutrition"))
async def cmd_nutrition(message: Message):
    """Handle /nutrition command - get personalized nutrition recommendations."""
    db = get_db_session()
    try:
        user_id = message.from_user.id
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        
        if not client:
            await message.answer("Сначала пройдите опросник /program для получения рекомендаций по питанию")
            return
        
        if not client.age or not client.weight or not client.height:
            await message.answer("Для получения рекомендаций по питанию необходимо указать возраст, вес и рост. Пройдите опросник /program")
            return
        
        # Get nutrition recommendations
        recommendations = await RecommendationService.get_nutrition_recommendations(db, client)
        
        if not recommendations:
            await message.answer("Не удалось сгенерировать рекомендации по питанию. Попробуйте позже.")
            return
        
        await message.answer(recommendations)
    except Exception as e:
        logger.error(f"Error getting nutrition recommendations: {e}")
        await message.answer("Произошла ошибка при получении рекомендаций по питанию. Попробуйте позже.")
    finally:
        db.close()


@router.message(Command("tips"))
async def cmd_tips(message: Message):
    """Handle /tips command - get personalized training tips."""
    db = get_db_session()
    try:
        user_id = message.from_user.id
        client = db.query(Client).filter(Client.telegram_id == user_id).first()
        
        if not client:
            await message.answer("Сначала пройдите опросник /program для получения советов по тренировкам")
            return
        
        # Get training tips
        tips = await RecommendationService.get_training_tips(db, client)
        
        if not tips:
            await message.answer("Не удалось сгенерировать советы по тренировкам. Попробуйте позже.")
            return
        
        await message.answer(tips)
    except Exception as e:
        logger.error(f"Error getting training tips: {e}")
        await message.answer("Произошла ошибка при получении советов по тренировкам. Попробуйте позже.")
    finally:
        db.close()

