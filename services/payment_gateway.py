from __future__ import annotations
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger
from database.models import WebsiteSettings
from services.payments_yookassa import create_yookassa_payment
from services.payments_tinkoff import create_tinkoff_payment

class PaymentGateway:
    @staticmethod
    def get_settings(db: Session) -> Dict[str, Any]:
        rows = db.query(WebsiteSettings).all()
        vals: Dict[str, Any] = {}
        for r in rows:
            vals[r.setting_key] = r.setting_value
        return vals

    @staticmethod
    def get_active_provider(db: Session) -> str:
        vals = PaymentGateway.get_settings(db)
        provider = (vals.get("payment_provider") or "yookassa").strip().lower()
        if provider not in ("yookassa", "tinkoff"):
            provider = "yookassa"
        return provider

    @staticmethod
    async def create_payment(
        db: Session,
        provider: Optional[str],
        amount: float,
        description: str,
        internal_payment_id: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        active = provider or PaymentGateway.get_active_provider(db)
        if active == "tinkoff":
            settings = PaymentGateway.get_settings(db)
            data = await create_tinkoff_payment(
                amount=amount,
                description=description,
                payment_id=internal_payment_id,
                customer_email=customer_email,
                override_terminal_key=settings.get("tinkoff_terminal_key"),
                override_secret_key=settings.get("tinkoff_secret_key"),
                override_return_url=settings.get("tinkoff_return_url"),
            )
            data["provider"] = active
            return data
        # default: yookassa
        settings = PaymentGateway.get_settings(db)
        data = await create_yookassa_payment(
            amount=amount,
            description=description,
            payment_id=internal_payment_id,
            metadata=metadata,
            customer_email=customer_email,
            override_shop_id=settings.get("yookassa_shop_id"),
            override_secret_key=settings.get("yookassa_secret_key"),
            override_return_url=settings.get("yookassa_return_url"),
        )
        data["provider"] = active
        return data

