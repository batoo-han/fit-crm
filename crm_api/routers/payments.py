"""Payments router for webhook and payment management."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from database.db import get_db_session
from database.models import Payment
from services.payment_service import PaymentService, PaymentService as PaymentServiceClass
from loguru import logger

router = APIRouter()


class YooKassaWebhookRequest(BaseModel):
    """YooKassa webhook request model."""
    type: str
    event: str
    object: dict


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
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
    }

