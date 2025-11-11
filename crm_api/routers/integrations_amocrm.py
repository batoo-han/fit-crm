from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.db import get_db_session
from crm_api.dependencies import get_current_user
from database.models_crm import User
from services.amocrm_service import AmoCrmService
from database.models import Client

router = APIRouter()


class ConnectPayload(BaseModel):
    domain: str
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_code: str | None = None


@router.get("/status")
async def get_status(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    enabled = AmoCrmService.is_enabled(db)
    creds = AmoCrmService.get_credentials(db)
    tokens = AmoCrmService.get_tokens(db)
    return {
        "enabled": enabled,
        "domain": creds.get("domain"),
        "has_tokens": bool(tokens),
        "expires_at": (tokens or {}).get("expires_at"),
    }


@router.post("/enable")
async def set_enabled(payload: dict, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    enabled = bool(payload.get("enabled", False))
    AmoCrmService.set_enabled(db, enabled)
    return {"enabled": enabled}


@router.post("/connect")
async def connect(payload: ConnectPayload, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    AmoCrmService.save_credentials(db, payload.domain, payload.client_id, payload.client_secret, payload.redirect_uri)
    if payload.auth_code:
        try:
            AmoCrmService.exchange_code_for_tokens(db, payload.auth_code)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


class PushClientPayload(BaseModel):
    client_id: int


@router.post("/push-client")
async def push_client(payload: PushClientPayload, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        contact_id = AmoCrmService.upsert_contact(db, client)
        return {"contact_id": contact_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


