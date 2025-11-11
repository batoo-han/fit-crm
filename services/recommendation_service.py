"""Service for generating personalized fitness recommendations."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger
from database.models import Client, TrainingProgram
from database.models_crm import PipelineStage
from services.ai_service import ai_service
import json


class RecommendationService:
    """Service for generating personalized fitness recommendations."""
    
    @staticmethod
    async def get_program_recommendation(
        db: Session,
        client: Client
    ) -> Dict[str, Any]:
        """
        Get personalized program recommendation for client.
        
        Args:
            db: Database session
            client: Client object
            
        Returns:
            Dictionary with recommendation details
        """
        # Build client profile
        profile = {
            "age": client.age,
            "gender": client.gender,
            "height": client.height,
            "weight": client.weight,
            "bmi": client.bmi,
            "experience_level": client.experience_level,
            "fitness_goals": client.fitness_goals,
            "health_restrictions": client.health_restrictions,
            "lifestyle": client.lifestyle,
            "location": client.location,
            "equipment": client.equipment,
        }
        
        # Determine recommended program type
        program_type = RecommendationService._determine_program_type(client)
        
        # Generate recommendation message
        message = await RecommendationService._generate_recommendation_message(client, program_type, profile)
        
        return {
            "program_type": program_type,
            "message": message,
            "reasoning": RecommendationService._get_reasoning(client, program_type)
        }
    
    @staticmethod
    def _determine_program_type(client: Client) -> str:
        """Determine recommended program type based on client data."""
        # Check if client has free program
        from handlers.start import has_free_program
        if client.id and has_free_program(client.id):
            return "paid_monthly"  # Recommend paid program after free
        
        # Check fitness goals
        if client.fitness_goals:
            goals = client.fitness_goals.lower()
            if "похудение" in goals or "снижение веса" in goals:
                return "paid_monthly"  # Weight loss needs ongoing support
            elif "набор массы" in goals or "масса" in goals:
                return "paid_3month"  # Muscle gain needs longer program
        
        # Check experience level
        if client.experience_level:
            level = client.experience_level.lower()
            if "новичок" in level:
                return "free_demo"  # Start with free demo
            elif "продвинутый" in level:
                return "paid_3month"  # Advanced users need longer program
        
        # Default recommendation
        return "free_demo"
    
    @staticmethod
    async def _generate_recommendation_message(
        client: Client,
        program_type: str,
        profile: Dict[str, Any]
    ) -> str:
        """Generate personalized recommendation message using AI."""
        program_names = {
            "free_demo": "бесплатная демо-программа на первую неделю",
            "paid_monthly": "персональное онлайн-сопровождение (1 месяц)",
            "paid_3month": "персональное онлайн-сопровождение (3 месяца)",
        }
        
        program_name = program_names.get(program_type, "программа тренировок")
        
        system_prompt = """Ты - AI-ассистент фитнес-тренера. Твоя задача - генерировать персонализированные рекомендации по программам тренировок для клиентов.

Анализируй данные клиента (возраст, пол, цели, опыт, ограничения) и генерируй убедительные, мотивирующие рекомендации.

Будь дружелюбным, профессиональным и конкретным. Объясняй, почему именно эта программа подходит клиенту."""
        
        user_prompt = f"""Данные клиента:
{json.dumps(profile, ensure_ascii=False, indent=2)}

Рекомендуемая программа: {program_name}

Сгенерируй персонализированное сообщение-рекомендацию для клиента, объясняя:
1. Почему именно эта программа подходит ему
2. Какие результаты он может ожидать
3. Что входит в программу
4. Как программа поможет достичь его целей

Будь конкретным и мотивирующим. Используй данные клиента для персонализации."""
        
        try:
            message = await ai_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.7
            )
            return message
        except Exception as e:
            logger.error(f"Error generating recommendation message: {e}")
            # Fallback message
            return f"""На основе ваших данных я рекомендую {program_name}.

Эта программа поможет вам достичь ваших целей и обеспечит необходимую поддержку на пути к результату."""
    
    @staticmethod
    def _get_reasoning(client: Client, program_type: str) -> str:
        """Get reasoning for program recommendation."""
        reasons = []
        
        if client.fitness_goals:
            reasons.append(f"Цель: {client.fitness_goals}")
        
        if client.experience_level:
            reasons.append(f"Уровень подготовки: {client.experience_level}")
        
        if client.age:
            reasons.append(f"Возраст: {client.age} лет")
        
        if program_type == "free_demo":
            reasons.append("Рекомендуем начать с бесплатной демо-программы")
        elif program_type == "paid_monthly":
            reasons.append("Рекомендуем месячную программу для достижения быстрых результатов")
        elif program_type == "paid_3month":
            reasons.append("Рекомендуем трехмесячную программу для максимального эффекта")
        
        return "; ".join(reasons) if reasons else "Общая рекомендация"
    
    @staticmethod
    async def get_nutrition_recommendations(
        db: Session,
        client: Client
    ) -> Optional[str]:
        """
        Get personalized nutrition recommendations for client.
        
        Args:
            db: Database session
            client: Client object
            
        Returns:
            Nutrition recommendations or None
        """
        if not client.age or not client.weight or not client.height:
            return None
        
        # Calculate daily calories (simplified)
        if client.gender == "мужской":
            bmr = 10 * client.weight + 6.25 * (client.height or 175) - 5 * client.age + 5
        else:
            bmr = 10 * client.weight + 6.25 * (client.height or 165) - 5 * client.age - 161
        
        # Adjust for activity level
        activity_multipliers = {
            "сидячий": 1.2,
            "умеренная активность": 1.55,
            "высокая активность": 1.725,
        }
        multiplier = activity_multipliers.get(client.lifestyle or "сидячий", 1.2)
        daily_calories = int(bmr * multiplier)
        
        # Adjust for goals
        if client.fitness_goals and ("похудение" in client.fitness_goals.lower() or "снижение веса" in client.fitness_goals.lower()):
            daily_calories -= 500  # Deficit for weight loss
        elif client.fitness_goals and ("набор массы" in client.fitness_goals.lower() or "масса" in client.fitness_goals.lower()):
            daily_calories += 300  # Surplus for muscle gain
        
        # Calculate macros (simplified)
        protein = int(daily_calories * 0.3 / 4)  # 30% calories from protein
        carbs = int(daily_calories * 0.45 / 4)  # 45% calories from carbs
        fats = int(daily_calories * 0.25 / 9)  # 25% calories from fats
        
        system_prompt = """Ты - AI-ассистент нутрициолога. Твоя задача - давать рекомендации по питанию для клиентов фитнес-тренера.

Будь конкретным, но не слишком техническим. Давай практические советы по питанию."""
        
        user_prompt = f"""Данные клиента:
- Возраст: {client.age} лет
- Пол: {client.gender or 'не указан'}
- Вес: {client.weight} кг
- Рост: {client.height} см
- Цель: {client.fitness_goals or 'не указана'}
- Ограничения: {client.nutrition or 'нет'}

Рассчитанные значения:
- Суточная калорийность: {daily_calories} ккал
- Белки: {protein} г
- Углеводы: {carbs} г
- Жиры: {fats} г

Дай персонализированные рекомендации по питанию для этого клиента. Включи:
1. Основные принципы питания
2. Рекомендации по распределению приемов пищи
3. Полезные продукты
4. Что ограничить или исключить
5. Особенности с учетом ограничений клиента (если есть)"""
        
        try:
            recommendations = await ai_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.7
            )
            return recommendations
        except Exception as e:
            logger.error(f"Error generating nutrition recommendations: {e}")
            return None
    
    @staticmethod
    async def get_training_tips(
        db: Session,
        client: Client
    ) -> Optional[str]:
        """
        Get personalized training tips for client.
        
        Args:
            db: Database session
            client: Client object
            
        Returns:
            Training tips or None
        """
        system_prompt = """Ты - AI-ассистент фитнес-тренера. Твоя задача - давать персонализированные советы по тренировкам для клиентов.

Будь конкретным, мотивирующим и практичным. Давай советы, которые клиент может применить сразу."""
        
        user_prompt = f"""Данные клиента:
- Возраст: {client.age or 'не указан'} лет
- Пол: {client.gender or 'не указан'}
- Уровень подготовки: {client.experience_level or 'не указан'}
- Цель: {client.fitness_goals or 'не указана'}
- Ограничения: {client.health_restrictions or 'нет'}
- Место тренировок: {client.location or 'не указано'}
- Оборудование: {client.equipment or 'не указано'}

Дай персонализированные советы по тренировкам для этого клиента. Включи:
1. Рекомендации по частоте тренировок
2. Продолжительность тренировок
3. Интенсивность
4. Особенности техники
5. Как избежать травм
6. Мотивационные советы"""
        
        try:
            tips = await ai_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.7
            )
            return tips
        except Exception as e:
            logger.error(f"Error generating training tips: {e}")
            return None


