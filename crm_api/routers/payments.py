"""Payments router for webhook and payment management."""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db_session
from database.models import Payment, PaymentWebhookLog, WebsiteSettings
from database.models_crm import User
from services.payment_service import PaymentService, PaymentService as PaymentServiceClass
from loguru import logger
from services.payments_tinkoff import verify_tinkoff_token, parse_tinkoff_status
from config import TINKOFF_SECRET_KEY
from services.payment_gateway import PaymentGateway
from crm_api.dependencies import get_current_user

router = APIRouter()


class YooKassaWebhookRequest(BaseModel):
    """YooKassa webhook request model."""
    type: str
    event: str
    object: dict


@router.get("/settings", status_code=status.HTTP_200_OK)
async def get_payment_settings(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return payment settings grouped in a flat dictionary."""
    rows = (
        db.query(WebsiteSettings)
        .filter(WebsiteSettings.category == "payments")
        .all()
    )
    result: Dict[str, Any] = {}
    for row in rows:
        value: Any = row.setting_value
        if row.setting_type == "json":
            try:
                value = json.loads(row.setting_value or "{}")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON setting {row.setting_key}")
        elif row.setting_type == "number":
            try:
                value = float(row.setting_value) if row.setting_value not in (None, "") else None
            except (TypeError, ValueError):
                value = row.setting_value
        elif row.setting_type == "boolean":
            value = str(row.setting_value).lower() == "true"
        result[row.setting_key] = value
    return result


@router.post("/settings", status_code=status.HTTP_200_OK)
async def update_payment_settings(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Upsert payment settings in a single request."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    existing_rows = (
        db.query(WebsiteSettings)
        .filter(WebsiteSettings.category == "payments")
        .all()
    )
    existing_map = {row.setting_key: row for row in existing_rows}

    updated = 0
    for key, value in payload.items():
        if value is None:
            stored_value = ""
            value_type = "string"
        elif isinstance(value, bool):
            stored_value = "true" if value else "false"
            value_type = "boolean"
        elif isinstance(value, (int, float)):
            stored_value = str(value)
            value_type = "number"
        elif isinstance(value, dict):
            stored_value = json.dumps(value, ensure_ascii=False)
            value_type = "json"
        else:
            stored_value = str(value)
            value_type = "string"

        setting = existing_map.get(key)
        if setting:
            setting.setting_value = stored_value
            setting.setting_type = value_type
            setting.category = setting.category or "payments"
            setting.updated_by = current_user.id if getattr(current_user, "id", None) else None
        else:
            setting = WebsiteSettings(
                setting_key=key,
                setting_value=stored_value,
                setting_type=value_type,
                category="payments",
                updated_by=current_user.id if getattr(current_user, "id", None) else None,
            )
            db.add(setting)
            existing_map[key] = setting
        updated += 1

    db.commit()
    return {"updated": updated}


@router.post("/webhook/yookassa", status_code=status.HTTP_200_OK)
async def yookassa_webhook(request: Request):
    """
    Handle YooKassa webhook notifications.
    
    YooKassa sends webhooks when payment status changes.
    """
    try:
        data = await request.json()
        event_type = data.get("event")
        payment_object = data.get("object", {})
        payment_id = payment_object.get("id")
        payment_status = payment_object.get("status")
        
        if not payment_id or not payment_status:
            logger.warning(f"Invalid webhook data: {data}")
            return {"status": "error", "message": "Invalid webhook data"}
        
        logger.info(f"Received YooKassa webhook: event={event_type}, payment_id={payment_id}, status={payment_status}")

        # Save webhook log
        try:
            db = get_db_session()
            log = PaymentWebhookLog(
                provider="yookassa",
                event=f"{event_type or ''} {payment_status or ''}".strip(),
                raw_payload=str(data),
            )
            db.add(log)
            db.commit()
        except Exception:
            pass
        
        # Update payment status
        updated = PaymentService.update_payment_from_webhook(
            payment_id=payment_id,
            status=payment_status,
            metadata=payment_object.get("metadata")
        )
        
        if updated:
            return {"status": "ok", "message": "Payment updated"}
        else:
            return {"status": "error", "message": "Payment not found or not updated"}
            
    except Exception as e:
        logger.error(f"Error processing YooKassa webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.post("/check-status", status_code=status.HTTP_200_OK)
async def check_payment_status(
    payment_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    Check payment status(es) from YooKassa.
    
    If payment_id is provided, checks that specific payment.
    Otherwise, checks all pending payments (up to limit).
    """
    try:
        if payment_id:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payment not found"
                )
            
            updated = PaymentService.check_payment_status(payment)
            return {
                "status": "ok",
                "payment_id": payment_id,
                "updated": updated,
                "current_status": payment.status
            }
        else:
            updated_count = PaymentService.check_pending_payments(limit=limit)
            return {
                "status": "ok",
                "updated_count": updated_count,
                "message": f"Checked pending payments, updated {updated_count}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking payment status: {str(e)}"
        )


@router.post("/webhook/tinkoff", status_code=status.HTTP_200_OK)
async def tinkoff_webhook(request: Request):
    """Handle Tinkoff notifications (JSON)."""
    try:
        data = await request.json()
        # Verify token
        if not verify_tinkoff_token(data, secret=TINKOFF_SECRET_KEY):
            logger.warning(f"Tinkoff webhook: invalid token {data}")
            return {"status": "error", "message": "Invalid token"}

        order_id = data.get("OrderId")
        payment_id = data.get("PaymentId")
        status_str = data.get("Status")
        if not order_id or not status_str:
            logger.warning(f"Tinkoff webhook: bad payload {data}")
            return {"status": "error", "message": "Bad payload"}

        internal_status = parse_tinkoff_status(status_str)

        # Save webhook log
        try:
            log = PaymentWebhookLog(
                provider="tinkoff",
                event=status_str,
                raw_payload=str(data),
            )
            db.add(log)
            db.commit()
        except Exception:
            pass
        db = get_db_session()
        updated = 0
        try:
            payment = db.query(Payment).filter(Payment.id == int(order_id)).first()
            if not payment:
                logger.warning(f"Tinkoff webhook: payment {order_id} not found")
                return {"status": "error", "message": "Payment not found"}
            old = payment.status
            payment.payment_id = payment_id or payment.payment_id
            payment.status = internal_status
            if internal_status == "completed" and old != "completed":
                payment.completed_at = datetime.utcnow()
                PaymentService._handle_payment_completed(db, payment)
            db.commit()
            updated = 1
        except Exception as e:
            logger.error(f"Tinkoff webhook error: {e}")
            db.rollback()
            return {"status": "error", "message": "Exception"}
        finally:
            db.close()
        return {"status": "ok", "updated": updated}
    except Exception as e:
        logger.error(f"Tinkoff webhook exception: {e}")
        return {"status": "error", "message": "Exception"}


class TestInitRequest(BaseModel):
    amount: float = 10.0
    description: Optional[str] = "Тестовый платёж"
    provider: Optional[str] = None  # yookassa | tinkoff | None (use active)


@router.post("/test-init", status_code=status.HTTP_200_OK)
async def test_init_payment(
    payload: TestInitRequest,
    db: Session = Depends(get_db_session),
    current_user: Optional[object] = None,
):
    """
    Create a test payment via active or specified provider without persisting Payment.
    Returns confirmation URL for manual check.
    """
    try:
        internal_id = f"test-{uuid.uuid4()}"
        result = await PaymentGateway.create_payment(
            db=db,
            provider=payload.provider,
            amount=payload.amount,
            description=payload.description or "Тестовый платёж",
            internal_payment_id=internal_id,
            customer_email=None,
        )
        url = result.get("confirmation", {}).get("confirmation_url")
        if not url:
            raise HTTPException(status_code=500, detail="Не удалось получить ссылку на оплату")
        return {"confirmation_url": url, "payment_id": result.get("id"), "internal_id": internal_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test init payment error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания тестового платежа")


@router.get("/health", status_code=status.HTTP_200_OK)
async def payments_health(
    provider: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    Simple provider check by trying to create a tiny test payment (1.00 RUB).
    """
    try:
        internal_id = f"health-{uuid.uuid4()}"
        result = await PaymentGateway.create_payment(
            db=db,
            provider=provider,
            amount=1.00,
            description="Health check",
            internal_payment_id=internal_id,
            customer_email=None,
        )
        url = result.get("confirmation", {}).get("confirmation_url")
        return {"ok": bool(url), "confirmation_url": url, "payment_id": result.get("id")}
    except Exception as e:
        logger.error(f"Payments health error: {e}")
        return {"ok": False, "error": "exception"}


@router.get("/{payment_id}", status_code=status.HTTP_200_OK)
async def get_payment(
    payment_id: int,
    db: Session = Depends(get_db_session)
):
    """Get payment details."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return {
        "id": payment.id,
        "client_id": payment.client_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_type": payment.payment_type,
        "status": payment.status,
        "payment_method": payment.payment_method,
        "payment_id": payment.payment_id,
        "promo_code": payment.promo_code,
        "discount_amount": payment.discount_amount,
        "final_amount": payment.final_amount,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
    }


@router.get("/webhooks/logs", status_code=status.HTTP_200_OK)
async def get_webhook_logs(limit: int = 50, db: Session = Depends(get_db_session)):
    rows = (
        db.query(PaymentWebhookLog)
        .order_by(PaymentWebhookLog.created_at.desc())
        .limit(max(1, min(200, limit)))
        .all()
    )
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "event": r.event,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
