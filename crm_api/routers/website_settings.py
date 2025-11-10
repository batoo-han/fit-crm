"""Website settings router."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from database.db import get_db_session
from database.models import WebsiteSettings
from database.models_crm import User
from crm_api.dependencies import get_current_user
from loguru import logger
import json
from datetime import datetime

router = APIRouter()


class SettingRequest(BaseModel):
    """Setting request model."""
    setting_key: str
    setting_value: str | Dict[str, Any] | None = None
    setting_type: str = "string"  # string, json, number, boolean
    category: str | None = None
    description: str | None = None


class SettingsResponse(BaseModel):
    """Settings response model."""
    settings: Dict[str, Any]
    categories: List[str]


class SettingResponse(BaseModel):
    """Single setting response model."""
    id: int
    setting_key: str
    setting_value: str | Dict[str, Any] | None
    setting_type: str
    category: str | None
    description: str | None
    updated_at: datetime
    updated_by: int | None

    class Config:
        from_attributes = True


@router.get("/settings", response_model=SettingsResponse)
async def get_all_settings(
    category: str | None = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get all website settings, optionally filtered by category."""
    query = db.query(WebsiteSettings)
    if category:
        query = query.filter(WebsiteSettings.category == category)
    
    settings_list = query.all()
    
    # Группируем по категориям
    settings_dict = {}
    categories = set()
    
    for setting in settings_list:
        cat = setting.category or "general"
        categories.add(cat)
        
        if cat not in settings_dict:
            settings_dict[cat] = {}
        
        # Парсим значение в зависимости от типа
        value = setting.setting_value
        if setting.setting_type == "json":
            try:
                value = json.loads(setting.setting_value or "{}")
            except:
                value = setting.setting_value
        elif setting.setting_type == "number":
            value = float(setting.setting_value) if setting.setting_value else None
        elif setting.setting_type == "boolean":
            value = setting.setting_value == "true"
        
        settings_dict[cat][setting.setting_key] = value
    
    return SettingsResponse(
        settings=settings_dict,
        categories=list(categories)
    )


@router.get("/settings/{setting_key}", response_model=SettingResponse)
async def get_setting(
    setting_key: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific setting by key."""
    setting = db.query(WebsiteSettings).filter(
        WebsiteSettings.setting_key == setting_key
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{setting_key}' not found"
        )
    
    return setting


@router.post("/settings", response_model=SettingResponse)
async def create_setting(
    setting_data: SettingRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new setting."""
    # Проверяем, существует ли уже настройка
    existing = db.query(WebsiteSettings).filter(
        WebsiteSettings.setting_key == setting_data.setting_key
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Setting '{setting_data.setting_key}' already exists. Use PUT to update."
        )
    
    # Преобразуем значение в строку
    value = setting_data.setting_value
    if setting_data.setting_type == "json" and isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    elif setting_data.setting_type == "boolean":
        value = "true" if value else "false"
    elif value is not None:
        value = str(value)
    
    setting = WebsiteSettings(
        setting_key=setting_data.setting_key,
        setting_value=value,
        setting_type=setting_data.setting_type,
        category=setting_data.category,
        description=setting_data.description,
        updated_by=current_user.id
    )
    
    db.add(setting)
    db.commit()
    db.refresh(setting)
    
    logger.info(f"Created setting: {setting_data.setting_key} by user {current_user.id}")
    
    return setting


@router.put("/settings/{setting_key}", response_model=SettingResponse)
async def update_setting(
    setting_key: str,
    setting_data: SettingRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update an existing setting."""
    setting = db.query(WebsiteSettings).filter(
        WebsiteSettings.setting_key == setting_key
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{setting_key}' not found"
        )
    
    # Преобразуем значение в строку
    value = setting_data.setting_value
    if setting_data.setting_type == "json" and isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    elif setting_data.setting_type == "boolean":
        value = "true" if value else "false"
    elif value is not None:
        value = str(value)
    
    # Обновляем поля
    setting.setting_value = value
    setting.setting_type = setting_data.setting_type
    if setting_data.category is not None:
        setting.category = setting_data.category
    if setting_data.description is not None:
        setting.description = setting_data.description
    setting.updated_by = current_user.id
    setting.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(setting)
    
    logger.info(f"Updated setting: {setting_key} by user {current_user.id}")
    
    return setting


@router.delete("/settings/{setting_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    setting_key: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a setting."""
    setting = db.query(WebsiteSettings).filter(
        WebsiteSettings.setting_key == setting_key
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{setting_key}' not found"
        )
    
    db.delete(setting)
    db.commit()
    
    logger.info(f"Deleted setting: {setting_key} by user {current_user.id}")
    
    return None


@router.post("/settings/batch", response_model=Dict[str, Any])
async def update_settings_batch(
    settings: Dict[str, Any],
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update multiple settings at once."""
    updated = []
    created = []
    errors = []
    
    for key, setting_data in settings.items():
        try:
            # Преобразуем setting_data в словарь если это Pydantic модель
            if hasattr(setting_data, 'model_dump'):
                setting_dict = setting_data.model_dump()
            elif hasattr(setting_data, 'dict'):
                setting_dict = setting_data.dict()
            elif isinstance(setting_data, dict):
                setting_dict = setting_data
            else:
                setting_dict = {"setting_value": setting_data}
            
            # Проверяем существование
            existing = db.query(WebsiteSettings).filter(
                WebsiteSettings.setting_key == key
            ).first()
            
            # Получаем параметры из словаря
            setting_type = setting_dict.get("setting_type", "string")
            value = setting_dict.get("setting_value")
            category = setting_dict.get("category")
            description = setting_dict.get("description")
            
            # Преобразуем значение
            if setting_type == "json" and isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            elif setting_type == "boolean":
                value = "true" if value else "false"
            elif value is not None:
                value = str(value)
            
            if existing:
                # Обновляем
                existing.setting_value = value
                existing.setting_type = setting_type
                if category is not None:
                    existing.category = category
                if description is not None:
                    existing.description = description
                existing.updated_by = current_user.id
                existing.updated_at = datetime.utcnow()
                updated.append(key)
            else:
                # Создаем
                new_setting = WebsiteSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type=setting_type,
                    category=category,
                    description=description,
                    updated_by=current_user.id
                )
                db.add(new_setting)
                created.append(key)
        except Exception as e:
            errors.append({"key": key, "error": str(e)})
            logger.error(f"Error updating setting {key}: {e}")
    
    db.commit()
    
    logger.info(f"Batch update: {len(updated)} updated, {len(created)} created, {len(errors)} errors by user {current_user.id}")
    
    return {
        "updated": updated,
        "created": created,
        "errors": errors
    }

