"""Promo code service for validating and applying discounts."""
from __future__ import annotations
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from database.models_crm import PromoCode, PromoUsage
from database.models import Client


class PromoService:
    @staticmethod
    def list_codes(db: Session) -> list[PromoCode]:
        return db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()

    @staticmethod
    def get_code(db: Session, code: str) -> Optional[PromoCode]:
        return db.query(PromoCode).filter(PromoCode.code == code).first()

    @staticmethod
    def create_code(db: Session, data: Dict[str, Any]) -> PromoCode:
        promo = PromoCode(**data)
        db.add(promo)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Промокод с таким кодом уже существует") from exc
        db.refresh(promo)
        return promo

    @staticmethod
    def update_code(db: Session, promo: PromoCode, data: Dict[str, Any]) -> PromoCode:
        for field, value in data.items():
            if hasattr(promo, field):
                setattr(promo, field, value)
        promo.updated_at = datetime.utcnow()
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Промокод с таким кодом уже существует") from exc
        db.refresh(promo)
        return promo

    @staticmethod
    def delete_code(db: Session, promo: PromoCode) -> None:
        db.delete(promo)
        db.commit()

    @staticmethod
    def validate_code(db: Session, code: str, client: Optional[Client] = None) -> Dict[str, Any]:
        promo = PromoService.get_code(db, code)
        if not promo or not promo.is_active:
            raise ValueError("Промокод не найден или не активен")
        now = datetime.utcnow()
        if promo.valid_from and now < promo.valid_from:
            raise ValueError("Промокод ещё не действует")
        if promo.valid_to and now > promo.valid_to:
            raise ValueError("Срок действия промокода истёк")
        if promo.max_usage and promo.used_count >= promo.max_usage:
            raise ValueError("Достигнут лимит использования промокода")
        if client and promo.per_client_limit:
            used = (
                db.query(PromoUsage)
                .filter(PromoUsage.promo_code_id == promo.id, PromoUsage.client_id == client.id)
                .count()
            )
            if used >= promo.per_client_limit:
                raise ValueError("Промокод уже использован максимальное количество раз этим клиентом")
        return {"promo": promo}

    @staticmethod
    def apply_discount(amount: float, promo: PromoCode) -> Dict[str, float]:
        discount = 0.0
        if promo.discount_type == "percent":
            discount = amount * (promo.discount_value / 100.0)
        else:
            discount = promo.discount_value
        discount = max(0.0, min(amount, discount))
        final_amount = amount - discount
        return {"discount": discount, "final_amount": final_amount}

    @staticmethod
    def register_usage(db: Session, promo: PromoCode, client_id: int, payment_id: Optional[int] = None) -> None:
        usage = PromoUsage(promo_code_id=promo.id, client_id=client_id, payment_id=payment_id)
        promo.used_count = (promo.used_count or 0) + 1
        db.add(usage)
        db.commit()


