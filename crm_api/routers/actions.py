"""Actions router."""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy.orm import Session

from crm_api.dependencies import get_current_user
from database.db import get_db_session
from database.models import Client
from database.models_crm import ClientAction, User, ActionType
from services.pipeline_service import PipelineAutomation

router = APIRouter()


class ClientActionResponse(BaseModel):
    id: int
    client_id: int
    action_type: str
    action_date: datetime | str
    description: str | None = None
    created_by: int | None = None

    @field_serializer("action_date")
    def serialize_datetime(self, value: datetime | str, _info) -> str:
        return value.isoformat() if isinstance(value, datetime) else value

    class Config:
        from_attributes = True


class ClientSnapshot(BaseModel):
    id: int
    pipeline_stage_id: int | None
    status: str | None
    last_contact_at: datetime | str | None = None
    next_contact_at: datetime | str | None = None

    @field_serializer("last_contact_at", "next_contact_at")
    def serialize_optional_datetime(self, value: datetime | str | None, _info) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        from_attributes = True


class ActionCreateRequest(BaseModel):
    client_id: int
    action_type: ActionType
    description: str | None = None
    action_date: datetime | None = None
    follow_up_hours: int | None = Field(
        default=None,
        ge=0,
        le=240,
        description="Через сколько часов запланировать следующий контакт (0 — очистить).",
    )


class ActionCreateResponse(BaseModel):
    action: ClientActionResponse
    automation: Dict[str, Any]
    client: ClientSnapshot


@router.get("")
async def get_actions(
    client_id: int | None = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get list of actions."""
    query = db.query(ClientAction)
    if client_id:
        query = query.filter(ClientAction.client_id == client_id)

    actions = query.order_by(ClientAction.action_date.desc()).limit(100).all()
    return actions


@router.post("", response_model=ActionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_action(
    action_data: ActionCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Create new action and apply pipeline automation."""
    client = db.query(Client).filter(Client.id == action_data.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    action = ClientAction(
        client_id=action_data.client_id,
        action_type=action_data.action_type.value,
        action_date=action_data.action_date or datetime.utcnow(),
        description=action_data.description,
        created_by=current_user.id,
    )
    db.add(action)

    automation = PipelineAutomation(db)
    automation_result = automation.handle_action_created(
        client=client,
        action=action,
        created_by=current_user.id,
        follow_up_hours_override=action_data.follow_up_hours,
    )

    db.commit()
    db.refresh(action)
    db.refresh(client)

    return ActionCreateResponse(
        action=ClientActionResponse.model_validate(action),
        automation=automation_result,
        client=ClientSnapshot.model_validate(client),
    )

