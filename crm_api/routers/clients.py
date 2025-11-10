"""Clients router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, field_serializer
from datetime import datetime
from database.db import get_db_session
from database.models import Client
from database.models_crm import User
from crm_api.dependencies import get_current_user
from loguru import logger

router = APIRouter()


class ClientResponse(BaseModel):
    id: int
    telegram_id: int
    first_name: str | None
    last_name: str | None
    telegram_username: str | None
    phone_number: str | None
    age: int | None
    gender: str | None
    status: str
    pipeline_stage_id: int | None
    created_at: datetime | str
    updated_at: datetime | str

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime | str, _info) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        from_attributes = True


class ClientDetailResponse(ClientResponse):
    """Extended client response with all fields."""
    height: int | None
    weight: float | None
    bmi: float | None
    experience_level: str | None
    fitness_goals: str | None
    health_restrictions: str | None
    lifestyle: str | None
    location: str | None
    equipment: str | None
    nutrition: str | None
    last_contact_at: datetime | str | None
    next_contact_at: datetime | str | None

    @field_serializer('last_contact_at', 'next_contact_at')
    def serialize_datetime_optional(self, value: datetime | str | None, _info) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class ClientCreateRequest(BaseModel):
    """Request model for creating a client."""
    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    telegram_username: str | None = None
    phone_number: str | None = None
    age: int | None = None
    gender: str | None = None
    height: int | None = None
    weight: float | None = None
    status: str = "new"
    pipeline_stage_id: int | None = None


@router.post("", response_model=ClientDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new client."""
    # Check if client with this telegram_id already exists
    existing = db.query(Client).filter(Client.telegram_id == client_data.telegram_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Client with telegram_id {client_data.telegram_id} already exists"
        )
    
    # Create new client
    client = Client(
        telegram_id=client_data.telegram_id,
        first_name=client_data.first_name,
        last_name=client_data.last_name,
        telegram_username=client_data.telegram_username,
        phone_number=client_data.phone_number,
        age=client_data.age,
        gender=client_data.gender,
        height=client_data.height,
        weight=client_data.weight,
        status=client_data.status,
        pipeline_stage_id=client_data.pipeline_stage_id,
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    logger.info(f"Client created: {client.id} (telegram_id: {client.telegram_id}) by user {current_user.id}")
    
    return ClientDetailResponse.model_validate(client)


@router.get("", response_model=List[ClientResponse])
async def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    pipeline_stage_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of clients with pagination and filters."""
    query = db.query(Client)
    
    if status:
        query = query.filter(Client.status == status)
    if pipeline_stage_id:
        query = query.filter(Client.pipeline_stage_id == pipeline_stage_id)
    
    clients = query.order_by(Client.created_at.desc()).offset(skip).limit(limit).all()
    # Convert to response models to ensure proper serialization
    return [ClientResponse.model_validate(client) for client in clients]


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get client details."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    return ClientDetailResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientDetailResponse)
async def update_client(
    client_id: int,
    client_data: dict,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update client information."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Update allowed fields
    allowed_fields = [
        "first_name", "last_name", "phone_number", "age", "gender",
        "height", "weight", "bmi", "experience_level", "fitness_goals",
        "health_restrictions", "lifestyle", "location", "equipment",
        "nutrition", "status", "pipeline_stage_id", "last_contact_at",
        "next_contact_at"
    ]
    
    for field, value in client_data.items():
        if field in allowed_fields and hasattr(client, field):
            setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    return ClientDetailResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    logger.info(f"Deleting client: {client_id} (telegram_id: {client.telegram_id}) by user {current_user.id}")
    
    # Удаляем связанные записи вручную (SQLite без каскадов)
    from database.models import Payment, TrainingProgram
    from database.models_crm import ClientPipeline, ClientAction, ClientContact, ProgressJournal

    # Порядок: журналы прогресса -> платежи -> программы -> pipeline/history/actions/contacts -> сам клиент
    db.query(ProgressJournal).filter(ProgressJournal.client_id == client_id).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.client_id == client_id).delete(synchronize_session=False)
    db.query(TrainingProgram).filter(TrainingProgram.client_id == client_id).delete(synchronize_session=False)
    db.query(ClientPipeline).filter(ClientPipeline.client_id == client_id).delete(synchronize_session=False)
    db.query(ClientAction).filter(ClientAction.client_id == client_id).delete(synchronize_session=False)
    db.query(ClientContact).filter(ClientContact.client_id == client_id).delete(synchronize_session=False)

    db.delete(client)
    db.commit()
    
    return None


@router.get("/{client_id}/payments")
async def get_client_payments(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get client payments."""
    from database.models import Payment
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    payments = db.query(Payment).filter(Payment.client_id == client_id).order_by(Payment.created_at.desc()).all()
    
    return [
        {
            "id": p.id,
            "amount": p.amount,
            "currency": p.currency,
            "payment_type": p.payment_type,
            "status": p.status,
            "payment_method": p.payment_method,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        }
        for p in payments
    ]


@router.get("/{client_id}/pipeline-history")
async def get_client_pipeline_history(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get client's pipeline movement history."""
    from database.models_crm import ClientPipeline, PipelineStage
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    history = db.query(ClientPipeline).filter(
        ClientPipeline.client_id == client_id
    ).order_by(ClientPipeline.moved_at.desc()).all()
    
    result = []
    for entry in history:
        stage = db.query(PipelineStage).filter(PipelineStage.id == entry.stage_id).first()
        result.append({
            "id": entry.id,
            "stage_id": entry.stage_id,
            "stage_name": stage.name if stage else "Unknown",
            "stage_color": stage.color if stage else "#000000",
            "moved_at": entry.moved_at.isoformat() if entry.moved_at else None,
            "moved_by": entry.moved_by,
            "notes": entry.notes,
        })
    
    return result

