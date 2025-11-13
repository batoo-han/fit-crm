"""Website contact form router."""
import json
import os
import re
import uuid
from datetime import datetime
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.db import get_db_session
from database.models import WebsiteContact, Client, Payment, WebsiteSettings
from database.models_crm import (
    PipelineStage,
    ClientPipeline,
    ClientAction,
    ClientContact,
    ActionType,
    ContactType,
    ContactDirection,
)
from loguru import logger
from config import TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, TELEGRAM_BOT_USERNAME
from services.bot_link_service import build_bot_invite_link, get_or_create_bot_link
from services.pipeline_service import PipelineAutomation
from services.payment_gateway import PaymentGateway
from services.promo_service import PromoService
from services.training_program_generator import program_generator
from services.program_formatter import ProgramFormatter
from services.website_catalog import get_service_config

INITIAL_FOLLOW_UP_HOURS = 12
ALLOWED_DELIVERY_CHANNELS = {"email", "telegram"}


router = APIRouter()


class ContactFormRequest(BaseModel):
    """Request model for website contact form."""
    name: str
    email: EmailStr
    phone: str | None = None
    service: str | None = None
    message: str | None = None


class PurchaseRequest(BaseModel):
    """Request model for purchasing a plan via website."""
    name: str
    email: EmailStr
    telegram_username: str | None = None
    phone: str | None = None
    service: str
    promo_code: str | None = None
    goal: str | None = None
    experience: str | None = None
    location: str | None = None
    gender: str | None = None
    age: int | None = None
    delivery_channels: List[str] | None = None
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
            service_config = get_service_config(form_data.service)
            service_name = service_config["title"] if service_config else form_data.service
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


async def send_purchase_notification(
    client_name: str,
    amount: float,
    service_title: str,
    payment_url: str,
    promo_code: str | None = None,
) -> bool:
    """Send notification about new purchase attempt."""
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        return False
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        lines = [
            "💳 Новая попытка оплаты на сайте",
            f"👤 Клиент: {client_name}",
            f"💼 Тариф: {service_title}",
            f"💰 Сумма: {amount:.2f} ₽",
        ]
        if promo_code:
            lines.append(f"🏷 Промокод: {promo_code}")
        lines.append(f"🔗 Ссылка оплаты:\n{payment_url}")
        lines.append(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text="\n".join(lines))
        await bot.session.close()
        return True
    except Exception as e:
        logger.error(f"Error sending purchase notification: {e}")
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
    
    # Try email lookup first
    if email:
        existing = db.query(Client).filter(Client.email == email).first()
        if existing:
            return existing
    
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
                email=form_data.email,
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
            if form_data.email and not getattr(client, "email", None):
                client.email = form_data.email
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
            service_config = get_service_config(form_data.service)
            service_name = service_config["title"] if service_config else form_data.service
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
        
    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        db.rollback()
        raise
    except Exception as e:
        # Логируем полную информацию об ошибке
        logger.error(f"Error processing contact form: {e}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Traceback: {error_trace}")
        db.rollback()
        
        # Возвращаем более информативное сообщение об ошибке
        error_detail = str(e) if str(e) else "Неизвестная ошибка"
        # В production не показываем технические детали, но логируем их
        if "ENVIRONMENT" in os.environ and os.environ.get("ENVIRONMENT") == "production":
            user_message = "Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже или свяжитесь с нами напрямую."
        else:
            user_message = f"Ошибка: {error_detail}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=user_message
        )
    finally:
        db.close()


@router.post("/purchase", status_code=status.HTTP_201_CREATED)
async def initiate_purchase(payload: PurchaseRequest):
    """Handle website purchase flow."""
    db = get_db_session()
    try:
        service_config = get_service_config(payload.service)
        if not service_config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный тариф для оплаты")

        delivery_channels = payload.delivery_channels or ["email"]
        invalid_channels = [ch for ch in delivery_channels if ch not in ALLOWED_DELIVERY_CHANNELS]
        if invalid_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некорректные каналы доставки: {', '.join(invalid_channels)}",
            )

        if payload.age is not None and payload.age < 10:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Возраст должен быть больше 10 лет")

        client = find_client_by_contact(payload.phone, payload.email, db)
        is_new_client = False

        if not client:
            min_telegram_id = db.query(Client.telegram_id).filter(Client.telegram_id < 0).order_by(Client.telegram_id.asc()).first()
            new_telegram_id = (min_telegram_id[0] - 1) if min_telegram_id else -1
            first_name = payload.name.split()[0] if payload.name else "Клиент"
            last_name = " ".join(payload.name.split()[1:]) if len(payload.name.split()) > 1 else None
            client = Client(
                telegram_id=new_telegram_id,
                first_name=first_name or "Клиент",
                last_name=last_name,
                phone_number=payload.phone,
                email=payload.email,
                telegram_username=payload.telegram_username,
                status="new",
            )
            db.add(client)
            db.commit()
            db.refresh(client)
            is_new_client = True
            logger.info(f"Created new client from purchase: {client.id} - {payload.name}")
        else:
            updated = False
            if payload.phone and not client.phone_number:
                client.phone_number = payload.phone
                updated = True
            if payload.email and not getattr(client, "email", None):
                client.email = payload.email
                updated = True
            if payload.telegram_username and not client.telegram_username:
                client.telegram_username = payload.telegram_username
                updated = True
            if payload.name and not client.first_name:
                name_parts = payload.name.split()
                client.first_name = name_parts[0] if name_parts else client.first_name or "Клиент"
                client.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else client.last_name
                updated = True
            if updated:
                db.commit()
                logger.info(f"Updated existing client {client.id} with contact info from purchase")

        profile_updated = False
        if payload.goal:
            client.fitness_goals = payload.goal
            profile_updated = True
        if payload.experience:
            client.experience_level = payload.experience
            profile_updated = True
        if payload.location:
            client.location = payload.location
            profile_updated = True
        if payload.gender:
            client.gender = payload.gender
            profile_updated = True
        if payload.age:
            client.age = payload.age
            profile_updated = True
        if profile_updated:
            db.commit()

        website_record = WebsiteContact(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            service=payload.service,
            message=payload.message or "Онлайн-покупка тарифа",
        )
        db.add(website_record)
        db.commit()

        amount = service_config["price"]
        discount = 0.0
        final_amount = amount

        if payload.promo_code:
            try:
                promo_data = PromoService.validate_code(db, payload.promo_code, client)
                discount_data = PromoService.apply_discount(amount, promo_data["promo"])
                discount = discount_data["discount"]
                final_amount = discount_data["final_amount"]
            except ValueError as promo_error:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(promo_error))

        final_amount = round(final_amount, 2)
        if final_amount < 1.0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сумма к оплате должна быть больше 1 ₽")

        automation = PipelineAutomation(db)
        if is_new_client:
            automation.move_client_to_stage_by_name(
                client=client,
                stage_name="Первичный контакт",
                notes="Автоматически добавлен после покупки на сайте",
            )

        service_title = service_config["title"]
        action_description = f"Сформирована ссылка на оплату (сайт): {service_title} — {final_amount:.2f} ₽"
        action = ClientAction(
            client_id=client.id,
            action_type=ActionType.PROPOSAL_SENT.value,
            action_date=datetime.utcnow(),
            description=action_description,
            created_by=None,
        )
        db.add(action)

        contact_record = ClientContact(
            client_id=client.id,
            contact_type=ContactType.EMAIL.value,
            contact_data=payload.email,
            message_text=payload.message or "Оформление покупки с сайта",
            direction=ContactDirection.INBOUND.value,
        )
        db.add(contact_record)
        db.flush()

        automation.handle_action_created(
            client=client,
            action=action,
            created_by=None,
            follow_up_hours_override=24,
        )

        internal_payment_id = f"web-{uuid.uuid4()}"
        provider_metadata = {
            "source": "website",
            "service": service_config["id"],
            "client_id": client.id,
            "internal_payment_id": internal_payment_id,
        }

        program_data = None
        formatted_program = None
        if service_config.get("auto_program"):
            gender_raw = (payload.gender or client.gender or "").lower()
            generator_gender = "female"
            if gender_raw.startswith("м") or gender_raw.startswith("m"):
                generator_gender = "male"
            location_value = payload.location or client.location or service_config.get("default_location") or "дом"
            age_value = payload.age or client.age or 30
            exp_raw = (payload.experience or client.experience_level or "").lower()
            if "нов" in exp_raw or "begin" in exp_raw:
                experience_code = "beginner"
            elif "прод" in exp_raw or "adv" in exp_raw:
                experience_code = "advanced"
            else:
                experience_code = "intermediate"
            goals_raw = (payload.goal or client.fitness_goals or "").lower()
            if "похуд" in goals_raw or "вес" in goals_raw:
                goal_code = "weight_loss"
            elif "мас" in goals_raw:
                goal_code = "muscle"
            elif "вынос" in goals_raw or "endur" in goals_raw:
                goal_code = "endurance"
            else:
                goal_code = "general"

            program_data = await program_generator.get_program_from_sheets(
                gender=generator_gender,
                age=age_value,
                experience=experience_code,
                goal=goal_code,
                location=location_value,
            )

            if program_data and service_config.get("weeks"):
                try:
                    weeks_limit = service_config["weeks"]
                    weeks_data = program_data.get("weeks", {})
                    program_data["weeks"] = {
                        wk: data for wk, data in weeks_data.items() if int(wk) <= weeks_limit
                    }
                except Exception as filter_error:
                    logger.warning(f"Cannot limit weeks for program preview: {filter_error}")

            if program_data:
                formatted_program = await ProgramFormatter.format_program(
                    program_data=program_data,
                    client_name=client.first_name or payload.name or "Клиент",
                )

        gateway_result = await PaymentGateway.create_payment(
            db=db,
            provider=None,
            amount=final_amount,
            description=service_title,
            internal_payment_id=internal_payment_id,
            customer_email=payload.email,
            metadata=provider_metadata,
        )

        confirmation_url = gateway_result.get("confirmation", {}).get("confirmation_url")
        provider_payment_id = gateway_result.get("id")
        payment_method = gateway_result.get("provider") or PaymentGateway.get_active_provider(db)

        if not confirmation_url or not provider_payment_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось получить ссылку оплаты")

        internal_metadata = {
            "source": "website",
            "service_id": service_config["id"],
            "program_type": service_config.get("program_type"),
            "weeks": service_config.get("weeks"),
            "location": payload.location or client.location or service_config.get("default_location"),
            "goal": payload.goal,
            "experience": payload.experience,
            "gender": payload.gender,
            "age": payload.age,
            "delivery_channels": delivery_channels,
            "message": payload.message,
            "promo_code": payload.promo_code,
            "client_email": payload.email,
            "internal_payment_id": internal_payment_id,
            "auto_program": service_config.get("auto_program", False),
            "program_data": program_data,
            "formatted_program": formatted_program,
        }

        payment = Payment(
            client_id=client.id,
            amount=amount,
            currency="RUB",
            payment_type=service_config["id"],
            status="pending",
            payment_method=payment_method,
            payment_id=provider_payment_id,
            promo_code=payload.promo_code,
            discount_amount=discount or None,
            final_amount=final_amount,
            payment_metadata=json.dumps(internal_metadata, ensure_ascii=False),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        bot_link = get_or_create_bot_link(
            db,
            client=client,
            source="website_purchase",
            context_data={
                "service": service_config["id"],
                "name": payload.name,
                "goal": payload.goal,
            },
        )
        bot_invite_url = build_bot_invite_link(bot_link.invite_token)

        await send_purchase_notification(
            client_name=payload.name,
            amount=final_amount,
            service_title=service_title,
            payment_url=confirmation_url,
            promo_code=payload.promo_code,
        )

        return {
            "success": True,
            "payment_url": confirmation_url,
            "payment_id": payment.id,
            "client_id": client.id,
            "amount": final_amount,
            "discount": discount,
            "bot_invite_link": bot_invite_url,
            "bot_invite_token": bot_link.invite_token,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error initiating purchase: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать платёж. Попробуйте позже или свяжитесь с тренером.",
        )
    finally:
        db.close()


@router.get("/settings/public")
async def get_public_widget_settings(
    category: str | None = None,
    db: Session = Depends(get_db_session)
):
    """Get public website settings (no authentication required)."""
    import json
    from typing import Dict, Any
    
    query = db.query(WebsiteSettings)
    if category:
        query = query.filter(WebsiteSettings.category == category)
    
    settings_list = query.all()
    
    # Вспомогательная функция нормализации ключей
    def normalize_key(cat: str | None, key: str) -> tuple[str, int]:
        if not key:
            return "", 0
        if not cat or cat == "general":
            return key, len(key)
        prefix = f"{cat}_"
        normalized = key
        while normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
        if not normalized:
            normalized = key
        return normalized, len(key)

    # Группируем по категориям
    settings_dict: Dict[str, Dict[str, Any]] = {}
    key_lengths: Dict[str, Dict[str, int]] = {}
    categories = set()
    
    for setting in settings_list:
        cat = setting.category or "general"
        categories.add(cat)
        
        if cat not in settings_dict:
            settings_dict[cat] = {}
            key_lengths[cat] = {}
        
        # Парсим значение в зависимости от типа
        value = setting.setting_value
        if setting.setting_type == "json":
            try:
                value = json.loads(setting.setting_value or "{}")
            except:
                value = setting.setting_value
        elif setting.setting_type == "number":
            value = float(setting.setting_value) if setting.setting_value else None
        elif setting.setting_type == "boolean":
            value = setting.setting_value == "true"
        
        normalized_key, original_length = normalize_key(cat, setting.setting_key)
        stored_length = key_lengths[cat].get(normalized_key)
        if stored_length is None or original_length <= stored_length:
            settings_dict[cat][normalized_key] = value
            key_lengths[cat][normalized_key] = original_length
    
    return {
        "settings": settings_dict,
        "categories": list(categories)
    }

