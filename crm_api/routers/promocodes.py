from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from database.db import get_db_session
from crm_api.dependencies import get_current_user
from database.models_crm import PromoCode, PromoUsage, User
from database.models import Client
from services.promo_service import PromoService

router = APIRouter()


class PromoBase(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: str = "percent"
    discount_value: float = 0
    max_usage: Optional[int] = None
    per_client_limit: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    is_active: bool = True


class PromoResponse(PromoBase):
    id: int
    used_count: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[PromoResponse])
async def list_promos(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    promos = PromoService.list_codes(db)
    return [PromoResponse.model_validate(p) for p in promos]


@router.post("", response_model=PromoResponse, status_code=status.HTTP_201_CREATED)
async def create_promo(payload: PromoBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    data = payload.model_dump()
    promo = PromoService.create_code(db, data)
    return PromoResponse.model_validate(promo)


@router.put("/{promo_id}", response_model=PromoResponse)
async def update_promo(promo_id: int, payload: PromoBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    promo = PromoService.update_code(db, promo, payload.model_dump())
    return PromoResponse.model_validate(promo)


@router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promo(promo_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    PromoService.delete_code(db, promo)
    return


class CheckPromoRequest(BaseModel):
    code: str
    amount: float
    client_id: Optional[int] = None


@router.post("/check")
async def check_promo(request: CheckPromoRequest, db: Session = Depends(get_db_session)):
    client = None
    if request.client_id:
        client = db.query(Client).filter(Client.id == request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    try:
        result = PromoService.validate_code(db, request.code, client)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    promo = result["promo"]
    discount_info = PromoService.apply_discount(request.amount, promo)
    return {"promo": PromoResponse.model_validate(promo), **discount_info}


