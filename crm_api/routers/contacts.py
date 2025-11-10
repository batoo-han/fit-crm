"""Contacts router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database.db import get_db_session
from database.models_crm import ClientContact, User
from crm_api.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def get_contacts(
    client_id: int | None = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of contacts."""
    query = db.query(ClientContact)
    if client_id:
        query = query.filter(ClientContact.client_id == client_id)
    
    contacts = query.order_by(ClientContact.created_at.desc()).limit(100).all()
    return contacts


@router.post("")
async def create_contact(
    contact_data: dict,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create new contact."""
    contact = ClientContact(**contact_data)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

