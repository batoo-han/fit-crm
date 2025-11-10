"""Progress journal router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from database.db import get_db_session
from database.models_crm import ProgressJournal, User
from database.models import Client
from crm_api.dependencies import get_current_user
from datetime import datetime

router = APIRouter()


class ProgressEntryResponse(BaseModel):
    id: int
    client_id: int
    program_id: int | None
    measurement_date: str
    period: str
    weight: float | None
    chest: float | None
    waist: float | None
    lower_abdomen: float | None
    glutes: float | None
    right_thigh: float | None
    left_thigh: float | None
    right_calf: float | None
    left_calf: float | None
    right_arm: float | None
    left_arm: float | None
    notes: str | None

    class Config:
        from_attributes = True


class CreateProgressEntryRequest(BaseModel):
    client_id: int
    program_id: int | None = None
    measurement_date: datetime | None = None
    period: str
    weight: float | None = None
    chest: float | None = None
    waist: float | None = None
    lower_abdomen: float | None = None
    glutes: float | None = None
    right_thigh: float | None = None
    left_thigh: float | None = None
    right_calf: float | None = None
    left_calf: float | None = None
    right_arm: float | None = None
    left_arm: float | None = None
    notes: str | None = None


@router.get("/{client_id}", response_model=List[ProgressEntryResponse])
async def get_client_progress(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get all progress entries for a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    entries = db.query(ProgressJournal).filter(
        ProgressJournal.client_id == client_id
    ).order_by(ProgressJournal.measurement_date.desc()).all()
    
    return entries


@router.post("", response_model=ProgressEntryResponse)
async def create_progress_entry(
    entry_data: CreateProgressEntryRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create new progress entry."""
    client = db.query(Client).filter(Client.id == entry_data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    entry = ProgressJournal(
        **entry_data.dict(exclude_none=True),
        measurement_date=entry_data.measurement_date or datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{client_id}/chart")
async def get_progress_chart(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get progress data formatted for chart display."""
    entries = db.query(ProgressJournal).filter(
        ProgressJournal.client_id == client_id
    ).order_by(ProgressJournal.measurement_date.asc()).all()
    
    # Format data for chart
    chart_data = {
        "periods": [entry.period for entry in entries],
        "weight": [entry.weight for entry in entries if entry.weight],
        "chest": [entry.chest for entry in entries if entry.chest],
        "waist": [entry.waist for entry in entries if entry.waist],
        "glutes": [entry.glutes for entry in entries if entry.glutes],
    }
    
    return chart_data

