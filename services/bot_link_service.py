"""Utilities for bridging website leads with Telegram bot."""
from __future__ import annotations

from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Optional, Tuple, Dict, Any
import json

from loguru import logger
from sqlalchemy.orm import Session

from config import TELEGRAM_BOT_USERNAME
from database.models import Client
from database.models_crm import ClientBotLink, ClientAction, ActionType
from services.pipeline_service import PipelineAutomation

TOKEN_BYTES = 8  # token_urlsafe(8) ~ 11 chars
DEFAULT_TOKEN_TTL_HOURS = 72


def _generate_unique_token(db: Session) -> str:
    """Generate unique invite token."""
    while True:
        token = token_urlsafe(TOKEN_BYTES)
        exists = db.query(ClientBotLink).filter(ClientBotLink.invite_token == token).first()
        if not exists:
            return token


def build_bot_invite_link(token: str) -> Optional[str]:
    """Build https link to Telegram bot with start payload."""
    if not TELEGRAM_BOT_USERNAME:
        return None
    return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={token}"


def get_or_create_bot_link(
    db: Session,
    client: Client,
    source: str = "website_contact",
    ttl_hours: int = DEFAULT_TOKEN_TTL_HOURS,
    context_data: Optional[Dict[str, Any]] = None,
) -> ClientBotLink:
    """
    Return existing unused bot link or create a new one.
    
    Args:
        db: Database session
        client: Client object
        source: Source of the link (e.g., "website_contact", "manual")
        ttl_hours: Time to live in hours
        context_data: Optional context data for personalization (service, message, etc.)
    """
    existing = (
        db.query(ClientBotLink)
        .filter(
            ClientBotLink.client_id == client.id,
            ClientBotLink.used_at.is_(None),
        )
        .order_by(ClientBotLink.created_at.desc())
        .first()
    )
    if existing:
        # Update context data if provided
        if context_data:
            existing.context_data = json.dumps(context_data, ensure_ascii=False)
            db.flush()
        return existing

    token = _generate_unique_token(db)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours) if ttl_hours else None
    link = ClientBotLink(
        client_id=client.id,
        invite_token=token,
        source=source,
        context_data=json.dumps(context_data, ensure_ascii=False) if context_data else None,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
    )
    db.add(link)
    db.flush()
    logger.info(f"Generated bot invite token for client {client.id}: {token}")
    return link


def use_bot_invite_token(
    db: Session,
    token: str,
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> Tuple[Optional[Client], bool, Optional[Dict[str, Any]]]:
    """
    Attach Telegram user to a client using invite token.

    Returns:
        (client, linked, context_data) - client object if linked, flag whether token was valid, context data for personalization.
    """
    if not token:
        return None, False, None

    link = (
        db.query(ClientBotLink)
        .filter(ClientBotLink.invite_token == token.strip())
        .first()
    )

    if not link or not link.client:
        logger.warning("Bot invite token not found or client missing: %s", token)
        return None, False, None

    if link.used_at and link.used_by_telegram_id and link.used_by_telegram_id != telegram_id:
        logger.warning(
            "Bot invite token %s already used by another Telegram ID (%s)",
            token,
            link.used_by_telegram_id,
        )
        return None, False, None

    client = link.client

    # Parse context data
    context_data = None
    if link.context_data:
        try:
            context_data = json.loads(link.context_data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse context_data for link {link.id}")

    # Update client record with Telegram info
    if client.telegram_id != telegram_id:
        client.telegram_id = telegram_id
    if username:
        client.telegram_username = username
    if first_name:
        client.first_name = first_name

    # Mark token as used
    link.used_at = datetime.utcnow()
    link.used_by_telegram_id = telegram_id

    # Log action for analytics / automation
    action_description = "Клиент подключился к Telegram через приглашение"
    if link.source == "website_contact":
        action_description += " с сайта"
        if context_data and context_data.get("service"):
            service_names = {
                "online-1-month": "Персональное онлайн-сопровождение (1 месяц)",
                "online-3-month": "Персональное онлайн-сопровождение (3 месяца)",
                "online-consultation": "Онлайн-консультация (1 час)",
                "offline-10-block": "Блок из 10 оффлайн-тренировок"
            }
            service_name = service_names.get(context_data.get("service"), context_data.get("service"))
            action_description += f" (интерес: {service_name})"
    
    action = ClientAction(
        client_id=client.id,
        action_type=ActionType.MESSAGE.value,
        action_date=datetime.utcnow(),
        description=action_description,
        created_by=None,
    )
    db.add(action)

    # Trigger automation (updates pipeline, reminders)
    automation = PipelineAutomation(db)
    automation.handle_action_created(client=client, action=action, created_by=None)

    logger.info(
        "Client %s linked to Telegram via token %s (username=%s, source=%s)",
        client.id,
        token,
        username,
        link.source,
    )

    return client, True, context_data

