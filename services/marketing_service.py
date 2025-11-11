from __future__ import annotations
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from database.models import Client
from database.models_crm import CampaignRun, CampaignMessage, CampaignAudience, ClientChannelPreference, CampaignDelivery
from loguru import logger
import json
import os
import requests
from datetime import datetime


class MarketingService:
    @staticmethod
    def _get_client_email(db: Session, client: Client) -> Optional[str]:
        # Try via ClientContact EMAIL
        from database.models_crm import ClientContact
        contact = (
            db.query(ClientContact)
            .filter(ClientContact.client_id == client.id, ClientContact.contact_type == "email")
            .order_by(ClientContact.id.desc())
            .first()
        )
        return contact.contact_data if contact and contact.contact_data and "@" in contact.contact_data else None

    @staticmethod
    def select_clients(db: Session, audience: Optional[CampaignAudience], limit: int = 100) -> List[Client]:
        q = db.query(Client)
        filters: Dict[str, Any] = {}
        if audience and audience.filter_json:
            try:
                filters = json.loads(audience.filter_json)
            except Exception:
                filters = {}
        # Simple filters: status, has_telegram, has_email
        status = filters.get("status")
        if status:
            q = q.filter(Client.status == status)
        if filters.get("has_telegram") is True:
            q = q.filter(Client.telegram_id.isnot(None))
        if filters.get("has_email") is True:
            # Join with contacts to ensure any email exists would be more correct; simple pass here
            pass
        return q.limit(limit).all()

    @staticmethod
    def _respect_preferences(db: Session, client: Client, channel: str) -> bool:
        pref = db.query(ClientChannelPreference).filter(ClientChannelPreference.client_id == client.id).first()
        if not pref:
            return True
        hour = datetime.utcnow().hour
        if pref.quiet_hours_start is not None and pref.quiet_hours_end is not None:
            if pref.quiet_hours_start <= pref.quiet_hours_end:
                if pref.quiet_hours_start <= hour < pref.quiet_hours_end:
                    return False
            else:
                # spans midnight
                if hour >= pref.quiet_hours_start or hour < pref.quiet_hours_end:
                    return False
        if channel == "telegram" and not pref.allow_telegram:
            return False
        if channel == "email" and not pref.allow_email:
            return False
        return True

    @staticmethod
    def _render_message(template: str, client: Client) -> str:
        try:
            text = template.format(
                first_name=client.first_name or "",
                last_name=client.last_name or "",
                username=client.telegram_username or "",
            )
            return text
        except Exception:
            return template

    @staticmethod
    def _send_telegram(client: Client, text: str) -> bool:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token or not client.telegram_id:
            return False
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": client.telegram_id, "text": text},
                timeout=15,
            )
            return resp.ok
        except Exception as e:
            logger.error(f"TG send error: {e}")
            return False

    @staticmethod
    def _send_email(address: str, subject: str, text: str) -> bool:
        import smtplib
        from email.message import EmailMessage
        host = os.getenv("SMTP_HOST"); port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER"); pwd = os.getenv("SMTP_PASSWORD")
        sender = os.getenv("SMTP_FROM", user or "")
        if not (host and user and pwd and sender and address and "@" in address):
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = address
            msg.set_content(text)
            with smtplib.SMTP(host, port) as s:
                s.starttls()
                s.login(user, pwd)
                s.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

    @staticmethod
    def process_run(db: Session, run: CampaignRun, limit: int = 100) -> int:
        # Choose message (first for now)
        msg = (
            db.query(CampaignMessage)
            .filter(CampaignMessage.campaign_id == run.campaign_id)
            .order_by(CampaignMessage.created_at.asc())
            .first()
        )
        if not msg:
            logger.warning(f"No message for campaign {run.campaign_id}")
            return 0
        audience = None
        if run.audience_id:
            audience = db.query(CampaignAudience).filter(CampaignAudience.id == run.audience_id).first()
        clients = MarketingService.select_clients(db, audience, limit=limit)
        run.total = len(clients); db.commit()

        sent = 0; errors = 0
        for client in clients:
            text = MarketingService._render_message(msg.body_text, client)
            ok_any = False
            # Deduplication: skip if recently sent for this campaign and channel (last 24h)
            def recently_sent(channel: str) -> bool:
                last = (
                    db.query(CampaignDelivery)
                    .filter(CampaignDelivery.campaign_id == run.campaign_id,
                            CampaignDelivery.client_id == client.id,
                            CampaignDelivery.channel == channel)
                    .order_by(CampaignDelivery.created_at.desc())
                    .first()
                )
                if not last:
                    return False
                try:
                    delta = datetime.utcnow() - last.created_at
                    return delta.total_seconds() < 24 * 3600
                except Exception:
                    return False

            # telegram
            if MarketingService._respect_preferences(db, client, "telegram") and not recently_sent("telegram"):
                ok_tg = MarketingService._send_telegram(client, text)
                if ok_tg:
                    db.add(CampaignDelivery(run_id=run.id, campaign_id=run.campaign_id, client_id=client.id, channel="telegram", status="sent"))
                else:
                    db.add(CampaignDelivery(run_id=run.id, campaign_id=run.campaign_id, client_id=client.id, channel="telegram", status="failed"))
                ok_any = ok_tg or ok_any
            # email
            email = MarketingService._get_client_email(db, client)
            if email and MarketingService._respect_preferences(db, client, "email") and not recently_sent("email"):
                ok_em = MarketingService._send_email(email, msg.title or "Сообщение", text)
                if ok_em:
                    db.add(CampaignDelivery(run_id=run.id, campaign_id=run.campaign_id, client_id=client.id, channel="email", status="sent"))
                else:
                    db.add(CampaignDelivery(run_id=run.id, campaign_id=run.campaign_id, client_id=client.id, channel="email", status="failed"))
                ok_any = ok_em or ok_any
            if ok_any:
                sent += 1
            else:
                errors += 1
        run.sent = sent; run.errors = errors
        db.commit()
        logger.info(f"Campaign run {run.id} sent={sent} errors={errors}")
        return len(clients)

    @staticmethod
    def _start_run(db: Session, campaign_id: int, audience_id: Optional[int], limit: int = 100) -> Optional[int]:
        run = CampaignRun(campaign_id=campaign_id, audience_id=audience_id, status="running", started_at=datetime.utcnow())
        db.add(run); db.commit(); db.refresh(run)
        MarketingService.process_run(db, run, limit=limit)
        run.status = "completed"; run.completed_at = datetime.utcnow()
        db.commit()
        return run.id

    @staticmethod
    def process_scheduled(db: Session, limit_per_run: int = 200, max_runs: int = 5) -> int:
        """Start runs for campaigns scheduled in the past and not yet executed today."""
        from database.models_crm import MarketingCampaign
        now = datetime.utcnow()
        candidates = (
            db.query(MarketingCampaign)
            .filter(MarketingCampaign.status.in_(["scheduled", "running"]))
            .filter(MarketingCampaign.schedule_at.isnot(None))
            .filter(MarketingCampaign.schedule_at <= now)
            .order_by(MarketingCampaign.schedule_at.asc())
            .limit(20)
            .all()
        )
        started = 0
        for c in candidates:
            try:
                # Frequency guard: if there is a completed run for this campaign within last 24h, skip
                last_run = (
                    db.query(CampaignRun)
                    .filter(CampaignRun.campaign_id == c.id)
                    .order_by(CampaignRun.started_at.desc().nullslast())
                    .first()
                )
                if last_run and last_run.started_at:
                    if (now - last_run.started_at).total_seconds() < 24 * 3600:
                        continue
                MarketingService._start_run(db, c.id, None, limit=limit_per_run)
                started += 1
                if started >= max_runs:
                    break
            except Exception as e:
                logger.error(f"Scheduled run error for campaign {c.id}: {e}")
        return started


