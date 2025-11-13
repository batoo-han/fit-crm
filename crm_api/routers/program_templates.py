"""Program templates router - CRUD operations for program templates."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database.db import get_db_session
from database.models_crm import ProgramTemplate, User
from crm_api.dependencies import get_current_user
from pydantic import BaseModel
from loguru import logger
from datetime import datetime
from typing import List, Optional
import json

router = APIRouter()


# Pydantic models
class ProgramTemplateCreate(BaseModel):
    """Модель для создания шаблона."""
    name: str
    template_type: str  # 'footer' or 'program'
    content: str
    description: Optional[str] = None
    placeholders: Optional[List[str]] = None
    is_active: bool = True
    is_default: bool = False


class ProgramTemplateUpdate(BaseModel):
    """Модель для обновления шаблона."""
    name: Optional[str] = None
    template_type: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    placeholders: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ProgramTemplateResponse(BaseModel):
    """Модель ответа для шаблона."""
    id: int
    name: str
    template_type: str
    content: str
    description: Optional[str]
    placeholders: Optional[List[str]]
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]
    updated_by: Optional[int]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


@router.get("/", response_model=List[ProgramTemplateResponse])
async def get_templates(
    template_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Получить список шаблонов."""
    query = db.query(ProgramTemplate)
    
    if template_type:
        query = query.filter(ProgramTemplate.template_type == template_type)
    if is_active is not None:
        query = query.filter(ProgramTemplate.is_active == is_active)
    
    templates = query.order_by(ProgramTemplate.created_at.desc()).all()
    
    # Parse placeholders JSON for each template and return as response models
    result = []
    for template in templates:
        template_dict = {
            "id": template.id,
            "name": template.name,
            "template_type": template.template_type,
            "content": template.content,
            "description": template.description,
            "placeholders": json.loads(template.placeholders) if template.placeholders else None,
            "is_active": template.is_active,
            "is_default": template.is_default,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "created_by": template.created_by,
            "updated_by": template.updated_by
        }
        result.append(ProgramTemplateResponse(**template_dict))
    
    return result


@router.get("/{template_id}", response_model=ProgramTemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Получить шаблон по ID."""
    template = db.query(ProgramTemplate).filter(ProgramTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    
    template_dict = {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type,
        "content": template.content,
        "description": template.description,
        "placeholders": json.loads(template.placeholders) if template.placeholders else None,
        "is_active": template.is_active,
        "is_default": template.is_default,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "created_by": template.created_by,
        "updated_by": template.updated_by
    }
    return ProgramTemplateResponse(**template_dict)


@router.get("/default/{template_type}", response_model=ProgramTemplateResponse)
async def get_default_template(
    template_type: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Получить шаблон по умолчанию для указанного типа."""
    template = db.query(ProgramTemplate).filter(
        ProgramTemplate.template_type == template_type,
        ProgramTemplate.is_default == True,
        ProgramTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Шаблон по умолчанию для типа '{template_type}' не найден")
    
    template_dict = {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type,
        "content": template.content,
        "description": template.description,
        "placeholders": json.loads(template.placeholders) if template.placeholders else None,
        "is_active": template.is_active,
        "is_default": template.is_default,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "created_by": template.created_by,
        "updated_by": template.updated_by
    }
    return ProgramTemplateResponse(**template_dict)


@router.post("/", response_model=ProgramTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: ProgramTemplateCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Создать новый шаблон."""
    # Проверка типа шаблона
    if template_data.template_type not in ['footer', 'program']:
        raise HTTPException(status_code=400, detail="Тип шаблона должен быть 'footer' или 'program'")
    
    # Если устанавливается как шаблон по умолчанию, снять флаг с других шаблонов того же типа
    if template_data.is_default:
        db.query(ProgramTemplate).filter(
            ProgramTemplate.template_type == template_data.template_type
        ).update({"is_default": False})
    
    # Преобразовать placeholders в JSON строку
    placeholders_json = json.dumps(template_data.placeholders, ensure_ascii=False) if template_data.placeholders else None
    
    template = ProgramTemplate(
        name=template_data.name,
        template_type=template_data.template_type,
        content=template_data.content,
        description=template_data.description,
        placeholders=placeholders_json,
        is_active=template_data.is_active,
        is_default=template_data.is_default,
        created_by=current_user.id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Created program template: {template.id} - {template.name} by user {current_user.id}")
    
    template_dict = {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type,
        "content": template.content,
        "description": template.description,
        "placeholders": json.loads(template.placeholders) if template.placeholders else None,
        "is_active": template.is_active,
        "is_default": template.is_default,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "created_by": template.created_by,
        "updated_by": template.updated_by
    }
    return ProgramTemplateResponse(**template_dict)


@router.put("/{template_id}", response_model=ProgramTemplateResponse)
async def update_template(
    template_id: int,
    template_data: ProgramTemplateUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Обновить шаблон."""
    template = db.query(ProgramTemplate).filter(ProgramTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    
    # Обновление полей
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.template_type is not None:
        if template_data.template_type not in ['footer', 'program']:
            raise HTTPException(status_code=400, detail="Тип шаблона должен быть 'footer' или 'program'")
        template.template_type = template_data.template_type
    if template_data.content is not None:
        template.content = template_data.content
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.placeholders is not None:
        template.placeholders = json.dumps(template_data.placeholders, ensure_ascii=False) if template_data.placeholders else None
    if template_data.is_active is not None:
        template.is_active = template_data.is_active
    if template_data.is_default is not None:
        template.is_default = template_data.is_default
        # Если устанавливается как шаблон по умолчанию, снять флаг с других шаблонов того же типа
        if template_data.is_default:
            db.query(ProgramTemplate).filter(
                ProgramTemplate.template_type == template.template_type,
                ProgramTemplate.id != template_id
            ).update({"is_default": False})
    
    template.updated_by = current_user.id
    template.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(template)
    
    logger.info(f"Updated program template: {template.id} - {template.name} by user {current_user.id}")
    
    template_dict = {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type,
        "content": template.content,
        "description": template.description,
        "placeholders": json.loads(template.placeholders) if template.placeholders else None,
        "is_active": template.is_active,
        "is_default": template.is_default,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "created_by": template.created_by,
        "updated_by": template.updated_by
    }
    return ProgramTemplateResponse(**template_dict)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Удалить шаблон."""
    template = db.query(ProgramTemplate).filter(ProgramTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    
    # Нельзя удалить шаблон по умолчанию
    if template.is_default:
        raise HTTPException(status_code=400, detail="Нельзя удалить шаблон по умолчанию. Сначала установите другой шаблон как шаблон по умолчанию.")
    
    db.delete(template)
    db.commit()
    
    logger.info(f"Deleted program template: {template_id} - {template.name} by user {current_user.id}")
    return None

