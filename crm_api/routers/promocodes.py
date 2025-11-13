from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from database.db import get_db_session
from crm_api.dependencies import get_current_user
from database.models_crm import PromoCode, PromoUsage, User
from database.models import Client
from services.promo_service import PromoService

router = APIRouter()


class PromoBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    discount_type: str = Field(default="percent")
    discount_value: float = Field(default=0)
    max_usage: Optional[int] = Field(default=None, ge=1)
    per_client_limit: Optional[int] = Field(default=None, ge=1)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: bool = True

    @field_validator("valid_from", "valid_to", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if value in (None, "", "null"):
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Дата должна быть в формате ISO 8601 (YYYY-MM-DD или YYYY-MM-DDTHH:MM)") from exc
        return value

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, value: str) -> str:
        allowed = {"percent", "fixed"}
        val = (value or "").strip().lower()
        if val not in allowed:
            raise ValueError(f"Тип скидки должен быть одним из: {', '.join(sorted(allowed))}")
        return val

    @field_validator("discount_value")
    @classmethod
    def validate_discount_value(cls, value: float, info):
        discount_type = info.data.get("discount_type", "percent")
        if discount_type == "percent":
            if value <= 0 or value > 100:
                raise ValueError("Процентная скидка должна быть в диапазоне 0 < value ≤ 100")
        else:
            if value <= 0:
                raise ValueError("Фиксированная скидка должна быть больше 0")
        return value

    @field_validator("valid_to")
    @classmethod
    def validate_valid_to(cls, value: Optional[datetime], info):
        valid_from = info.data.get("valid_from")
        if value and valid_from and value <= valid_from:
            raise ValueError("Дата окончания действия должна быть позже даты начала")
        return value


class PromoResponse(PromoBase):
    id: int
    used_count: int

    model_config = {"from_attributes": True}


@router.get("", response_model=List[PromoResponse])
async def list_promos(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    promos = PromoService.list_codes(db)
    return [PromoResponse.model_validate(p) for p in promos]


@router.post("", response_model=PromoResponse, status_code=status.HTTP_201_CREATED)
async def create_promo(payload: PromoBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    data = payload.model_dump()
    try:
        promo = PromoService.create_code(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PromoResponse.model_validate(promo)


@router.put("/{promo_id}", response_model=PromoResponse)
async def update_promo(promo_id: int, payload: PromoBase, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    try:
        promo = PromoService.update_code(db, promo, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


