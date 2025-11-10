"""Actions router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database.db import get_db_session
from database.models_crm import ClientAction, User
from crm_api.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def get_actions(
    client_id: int | None = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of actions."""
    query = db.query(ClientAction)
    if client_id:
        query = query.filter(ClientAction.client_id == client_id)
    
    actions = query.order_by(ClientAction.action_date.desc()).limit(100).all()
    return actions


@router.post("")
async def create_action(
    action_data: dict,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create new action."""
    action = ClientAction(**action_data, created_by=current_user.id)
    db.add(action)
    db.commit()
    db.refresh(action)
    return action

