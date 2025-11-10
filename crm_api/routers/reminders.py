"""Reminders router for processing automated reminders."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from database.db import get_db_session
from database.models_crm import Reminder
from services.reminder_service import ReminderService
from loguru import logger
from datetime import datetime

router = APIRouter()


class ReminderResponse(BaseModel):
    id: int
    client_id: int
    program_id: int | None
    reminder_type: str
    scheduled_at: datetime | str
    sent_at: datetime | str | None
    is_sent: bool
    message_text: str | None

    class Config:
        from_attributes = True


@router.post("/process", status_code=status.HTTP_200_OK)
async def process_reminders(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    Process due reminders.
    
    This endpoint should be called periodically (e.g., via cron job) to process reminders.
    """
    try:
        reminders = ReminderService.get_due_reminders(limit=limit)
        
        if not reminders:
            return {
                "message": "No due reminders",
                "processed": 0
            }
        
        processed_count = 0
        for reminder in reminders:
            try:
                success = ReminderService.process_reminder(reminder)
                if success:
                    processed_count += 1
            except Exception as e:
                logger.error(f"Error processing reminder {reminder.id}: {e}")
        
        return {
            "message": f"Processed {processed_count} reminders",
            "processed": processed_count,
            "total": len(reminders)
        }
        
    except Exception as e:
        logger.error(f"Error processing reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing reminders: {str(e)}"
        )


@router.get("", response_model=List[ReminderResponse])
async def get_reminders(
    client_id: int | None = None,
    is_sent: bool | None = None,
    db: Session = Depends(get_db_session)
):
    """Get reminders with optional filters."""
    query = db.query(Reminder)
    
    if client_id:
        query = query.filter(Reminder.client_id == client_id)
    
    if is_sent is not None:
        query = query.filter(Reminder.is_sent == is_sent)
    
    reminders = query.order_by(Reminder.scheduled_at.desc()).limit(100).all()
    return reminders

