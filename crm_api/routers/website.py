"""Website contact form router."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.db import get_db_session
from database.models import WebsiteContact, Client
from database.models_crm import PipelineStage, ClientPipeline, ClientAction, ClientContact, ActionType, ContactType, ContactDirection
from datetime import datetime
from loguru import logger
from config import TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, TELEGRAM_BOT_USERNAME
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
import re
from services.pipeline_service import PipelineAutomation
from services.bot_link_service import (
    get_or_create_bot_link,
    build_bot_invite_link,
)

INITIAL_FOLLOW_UP_HOURS = 12

router = APIRouter()


class ContactFormRequest(BaseModel):
    """Request model for website contact form."""
    name: str
    email: EmailStr
    phone: str | None = None
    service: str | None = None
    message: str | None = None


async def send_telegram_notification(form_data: ContactFormRequest, bot_invite_url: str | None = None) -> bool:
    """Send notification to owner via Telegram bot."""
    try:
        if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
            logger.warning("Telegram bot token or admin chat ID not configured")
            return False
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Формируем сообщение
        message_text = f"""🔔 Новая заявка с сайта

👤 Имя: {form_data.name}
📧 Email: {form_data.email}"""
        
        if form_data.phone:
            message_text += f"\n📞 Телефон: {form_data.phone}"
        
        if form_data.service:
            service_names = {
                "online-1-month": "Персональное онлайн-сопровождение (1 месяц)",
                "online-3-month": "Персональное онлайн-сопровождение (3 месяца)",
                "online-consultation": "Онлайн-консультация (1 час)",
                "offline-10-block": "Блок из 10 оффлайн-тренировок"
            }
            service_name = service_names.get(form_data.service, form_data.service)
            message_text += f"\n💼 Услуга: {service_name}"
        
        if form_data.message:
            message_text += f"\n\n💬 Сообщение:\n{form_data.message}"
        
        if bot_invite_url:
            message_text += f"\n\n🤖 Пригласительная ссылка: {bot_invite_url}"
        
        message_text += f"\n\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        # Отправляем сообщение
        await bot.send_message(
            chat_id=int(ADMIN_CHAT_ID),
            text=message_text
        )
        
        await bot.session.close()
        return True
        
    except TelegramBadRequest as e:
        logger.error(f"Telegram API error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False


def normalize_phone(phone: str | None) -> str | None:
    """Normalize phone number for comparison (remove spaces, brackets, dashes)."""
    if not phone:
        return None
    # Удаляем все символы кроме цифр и +
    normalized = re.sub(r'[^\d+]', '', phone)
    # Если начинается с +7, заменяем на 7
    if normalized.startswith('+7'):
        normalized = '7' + normalized[2:]
    # Если начинается с 8, заменяем на 7
    if normalized.startswith('8') and len(normalized) == 11:
        normalized = '7' + normalized[1:]
    return normalized


def find_client_by_contact(phone: str | None, email: str | None, db: Session) -> Client | None:
    """Find client by phone or email."""
    if not phone and not email:
        return None
    
    # Ищем по телефону
    if phone:
        normalized_phone = normalize_phone(phone)
        if normalized_phone:
            # Получаем последние 10 цифр для поиска
            last_10_digits = normalized_phone[-10:] if len(normalized_phone) >= 10 else normalized_phone
            
            # Ищем клиента с таким телефоном (сравниваем нормализованные версии)
            all_clients = db.query(Client).filter(
                Client.phone_number.isnot(None)
            ).all()
            
            for client in all_clients:
                if client.phone_number:
                    client_normalized = normalize_phone(client.phone_number)
                    if client_normalized:
                        # Сравниваем последние 10 цифр
                        client_last_10 = client_normalized[-10:] if len(client_normalized) >= 10 else client_normalized
                        if client_last_10 == last_10_digits:
                            return client
                        # Также проверяем точное совпадение
                        if client_normalized == normalized_phone:
                            return client
    
    # Ищем по email через контакты (если в будущем добавим поле email в Client)
    # Пока ищем только по телефону
    return None


def get_primary_contact_stage(db: Session) -> PipelineStage | None:
    """Get 'Первичный контакт' pipeline stage."""
    stage = db.query(PipelineStage).filter(
        PipelineStage.name == "Первичный контакт",
        PipelineStage.is_active == True
    ).first()
    
    # Если не нашли по имени, берем первый этап по order
    if not stage:
        stage = db.query(PipelineStage).filter(
            PipelineStage.is_active == True
        ).order_by(PipelineStage.order).first()
    
    return stage


@router.post("/contact", status_code=status.HTTP_201_CREATED)
async def submit_contact_form(form_data: ContactFormRequest):
    """Handle website contact form submission."""
    db = get_db_session()
    try:
        # Сохраняем заявку в БД
        contact = WebsiteContact(
            name=form_data.name,
            email=form_data.email,
            phone=form_data.phone,
            service=form_data.service,
            message=form_data.message
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        
        logger.info(f"Website contact form submitted: {contact.id} - {form_data.name} ({form_data.email})")
        
        # Ищем существующего клиента по телефону
        client = find_client_by_contact(form_data.phone, form_data.email, db)
        is_new_client = False
        
        if not client:
            # Создаем нового клиента
            # Для клиентов с сайта telegram_id будет отрицательным (уникальный ID)
            # Находим минимальный отрицательный telegram_id и используем следующий
            min_telegram_id = db.query(Client.telegram_id).filter(
                Client.telegram_id < 0
            ).order_by(Client.telegram_id.asc()).first()
            
            if min_telegram_id:
                new_telegram_id = min_telegram_id[0] - 1
            else:
                new_telegram_id = -1  # Первый клиент с сайта
            
            client = Client(
                telegram_id=new_telegram_id,
                first_name=form_data.name.split()[0] if form_data.name else "Клиент",
                last_name=" ".join(form_data.name.split()[1:]) if len(form_data.name.split()) > 1 else None,
                phone_number=form_data.phone,
                status="new"
            )
            db.add(client)
            db.commit()
            db.refresh(client)
            is_new_client = True
            logger.info(f"Created new client from website: {client.id} - {form_data.name}")
        else:
            # Обновляем информацию о клиенте если нужно
            if form_data.phone and not client.phone_number:
                client.phone_number = form_data.phone
            if form_data.name and not client.first_name:
                name_parts = form_data.name.split()
                client.first_name = name_parts[0] if name_parts else "Клиент"
                if len(name_parts) > 1:
                    client.last_name = " ".join(name_parts[1:])
            db.commit()
            logger.info(f"Found existing client: {client.id} - {form_data.name}")
        
        automation = PipelineAutomation(db)
        if not is_new_client and not client.pipeline_stage_id:
            automation.move_client_to_stage_by_name(
                client=client,
                stage_name="Первичный контакт",
                notes="Автоматически добавлен в первичный этап после заявки с сайта",
            )
        
        # Если новый клиент - перемещаем в воронку на этап "Первичный контакт"
        if is_new_client:
            moved = automation.move_client_to_stage_by_name(
                client=client,
                stage_name="Первичный контакт",
                notes="Автоматически добавлен из формы обратной связи на сайте",
            )
            if moved:
                db.flush()
                logger.info(f"Moved client {client.id} to pipeline stage 'Первичный контакт'")
        
        # Создаем действие (ClientAction)
        action_description = f"Заявка с сайта"
        if form_data.service:
            service_names = {
                "online-1-month": "Персональное онлайн-сопровождение (1 месяц)",
                "online-3-month": "Персональное онлайн-сопровождение (3 месяца)",
                "online-consultation": "Онлайн-консультация (1 час)",
                "offline-10-block": "Блок из 10 оффлайн-тренировок"
            }
            service_name = service_names.get(form_data.service, form_data.service)
            action_description += f": {service_name}"
        if form_data.message:
            action_description += f"\nСообщение: {form_data.message[:200]}"
        
        action = ClientAction(
            client_id=client.id,
            action_type=ActionType.OTHER.value,
            action_date=datetime.utcnow(),
            description=action_description,
            created_by=None  # Система
        )
        db.add(action)
        
        # Создаем контакт (ClientContact)
        contact_entry = ClientContact(
            client_id=client.id,
            contact_type=ContactType.EMAIL.value if form_data.email else ContactType.PHONE.value,
            contact_data=form_data.email or form_data.phone or "",
            message_text=form_data.message,
            direction=ContactDirection.INBOUND.value
        )
        db.add(contact_entry)
        
        # Обновляем сроки контактов и напоминания
        automation.handle_action_created(
            client=client,
            action=action,
            created_by=None,
            follow_up_hours_override=INITIAL_FOLLOW_UP_HOURS,
        )

        # Generate bot invite link with context data for personalization
        context_data = {
            "source": "website_contact",
            "service": form_data.service,
            "message": form_data.message,
            "name": form_data.name,
        }
        bot_link = get_or_create_bot_link(
            db, 
            client=client, 
            source="website_contact",
            context_data=context_data
        )
        bot_invite_url = build_bot_invite_link(bot_link.invite_token)

        db.commit()
        logger.info(f"Created action and contact for client {client.id}")
        
        # Отправляем уведомление в Telegram
        notification_sent = await send_telegram_notification(form_data, bot_invite_url)
        if not notification_sent:
            logger.warning(f"Failed to send Telegram notification for contact {contact.id}")
        
        response = {
            "success": True,
            "message": "Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.",
            "contact_id": contact.id,
            "client_id": client.id,
            "is_new_client": is_new_client,
            "bot_invite_token": bot_link.invite_token,
            "bot_invite_link": bot_invite_url,
            "bot_username": TELEGRAM_BOT_USERNAME,
        }

        if bot_link.expires_at:
            response["bot_invite_expires_at"] = bot_link.expires_at.isoformat()

        return response
        
    except Exception as e:
        logger.error(f"Error processing contact form: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже."
        )
    finally:
        db.close()

