"""Service for generating personalized welcome messages for clients."""
from typing import Optional, Dict, Any

from config import TRAINER_NAME, PRICE_ONLINE_1_MONTH, PRICE_ONLINE_3_MONTHS, PRICE_CONSULTATION
from database.models import Client


class WelcomeService:
    """Service for generating personalized welcome messages."""
    
    @staticmethod
    def get_welcome_message(
        client: Client,
        is_new_client: bool,
        context_data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> str:
        """
        Generate personalized welcome message based on client context.
        
        Args:
            client: Client object
            is_new_client: Whether this is a new client
            context_data: Optional context data from bot link (service, message, etc.)
            source: Source of the client (e.g., "website_contact", "direct")
            
        Returns:
            Welcome message text
        """
        first_name = client.first_name or "друг"
        
        # Если клиент пришел с сайта через deep link
        if source == "website_contact" and context_data:
            return WelcomeService._get_website_welcome_message(
                first_name=first_name,
                context_data=context_data
            )
        
        # Стандартное приветствие для новых клиентов
        if is_new_client:
            return WelcomeService._get_default_welcome_message(first_name)
        
        # Приветствие для существующих клиентов
        return WelcomeService._get_returning_welcome_message(first_name)
    
    @staticmethod
    def _get_website_welcome_message(first_name: str, context_data: Dict[str, Any]) -> str:
        """Generate welcome message for website leads."""
        service = context_data.get("service")
        message = context_data.get("message")
        
        # Маппинг услуг
        service_names = {
            "online-1-month": {
                "name": "Персональное онлайн-сопровождение (1 месяц)",
                "price": f"{PRICE_ONLINE_1_MONTH:,}₽",
                "description": "Индивидуальный план тренировок и питания с ежедневной поддержкой"
            },
            "online-3-month": {
                "name": "Персональное онлайн-сопровождение (3 месяца)",
                "price": f"{PRICE_ONLINE_3_MONTHS:,}₽",
                "description": "Индивидуальный план тренировок и питания с ежедневной поддержкой"
            },
            "online-consultation": {
                "name": "Онлайн-консультация (1 час)",
                "price": f"{PRICE_CONSULTATION:,}₽",
                "description": "Персональная консультация с анализом текущего состояния"
            },
            "offline-10-block": {
                "name": "Блок из 10 оффлайн-тренировок",
                "price": "По запросу",
                "description": "Оффлайн-тренировки в зале"
            }
        }
        
        service_info = service_names.get(service, {})
        
        welcome_text = f"""🎯 Привет, {first_name}! Меня зовут {TRAINER_NAME}.

Спасибо, что обратились ко мне! Я получил вашу заявку с сайта и готов помочь вам достичь ваших фитнес-целей."""
        
        # Добавляем информацию об услуге, если она была указана
        if service_info:
            welcome_text += f"""

💼 Вы интересовались услугой:
• {service_info.get('name', service)}
• {service_info.get('description', '')}
• Стоимость: {service_info.get('price', 'По запросу')}"""
        
        # Добавляем информацию о сообщении, если оно было
        if message:
            welcome_text += f"""

📝 Я видел ваше сообщение. Обязательно учту все пожелания при подготовке программы!"""
        
        welcome_text += f"""

🎁 Для начала предлагаю получить бесплатную программу тренировок на первую неделю. Это поможет вам:
• Понять, подходит ли вам мой подход
• Ощутить первые результаты
• Принять решение о дальнейшем сотрудничестве

Готовы начать? Выберите действие ниже 👇"""
        
        return welcome_text
    
    @staticmethod
    def _get_default_welcome_message(first_name: str) -> str:
        """Generate default welcome message for new clients."""
        return f"""🏋️ Привет, {first_name}! Меня зовут {TRAINER_NAME}.

Я помогу тебе достичь твоих фитнес-целей! 

🎯 Что я могу предложить:
• Персональную программу тренировок
• План питания с расчетом КБЖУ
• Ежедневную поддержку и мотивацию
• Видео-демонстрации упражнений
• Онлайн-тренировки с тренером

Выбери, что тебе интересно 👇"""
    
    @staticmethod
    def _get_returning_welcome_message(first_name: str) -> str:
        """Generate welcome message for returning clients."""
        return f"""🏋️ С возвращением, {first_name}!

Я помогу тебе достичь твоих фитнес-целей! 

Выбери, что тебе интересно 👇"""

