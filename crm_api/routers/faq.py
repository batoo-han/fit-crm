"""FAQ router for managing FAQ items."""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from database.db import get_db_session
from database.models_crm import FAQ
from services.faq_service import FAQService
from loguru import logger
import json

router = APIRouter()


class FAQResponse(BaseModel):
    """FAQ response model."""
    id: int
    question: str
    answer: str
    category: Optional[str]
    keywords: Optional[List[str]]
    priority: int
    is_active: bool
    use_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class FAQCreateRequest(BaseModel):
    """FAQ create request model."""
    question: str
    answer: str
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    priority: int = 0


class FAQUpdateRequest(BaseModel):
    """FAQ update request model."""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class FAQSearchRequest(BaseModel):
    """FAQ search request model."""
    query: str
    category: Optional[str] = None
    limit: int = 5


@router.get("", response_model=List[FAQResponse])
async def get_faq(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db_session),
):
    """Get all FAQ items, optionally filtered."""
    faq_items = FAQService.get_all_faq(db, category=category, is_active=is_active)
    
    result = []
    for faq in faq_items:
        keywords = None
        if faq.keywords:
            try:
                keywords = json.loads(faq.keywords)
            except:
                keywords = None
        
        result.append(FAQResponse(
            id=faq.id,
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            keywords=keywords,
            priority=faq.priority,
            is_active=faq.is_active,
            use_count=faq.use_count,
            created_at=faq.created_at.isoformat() if faq.created_at else "",
            updated_at=faq.updated_at.isoformat() if faq.updated_at else "",
        ))
    
    return result


@router.get("/{faq_id}", response_model=FAQResponse)
async def get_faq_by_id(
    faq_id: int,
    db: Session = Depends(get_db_session),
):
    """Get FAQ by ID."""
    faq = FAQService.get_faq_by_id(db, faq_id)
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    
    keywords = None
    if faq.keywords:
        try:
            keywords = json.loads(faq.keywords)
        except:
            keywords = None
    
    return FAQResponse(
        id=faq.id,
        question=faq.question,
        answer=faq.answer,
        category=faq.category,
        keywords=keywords,
        priority=faq.priority,
        is_active=faq.is_active,
        use_count=faq.use_count,
        created_at=faq.created_at.isoformat() if faq.created_at else "",
        updated_at=faq.updated_at.isoformat() if faq.updated_at else "",
    )


@router.post("", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    faq_data: FAQCreateRequest,
    db: Session = Depends(get_db_session),
):
    """Create new FAQ item."""
    faq = FAQService.create_faq(
        db=db,
        question=faq_data.question,
        answer=faq_data.answer,
        category=faq_data.category,
        keywords=faq_data.keywords,
        priority=faq_data.priority,
        created_by=None,  # TODO: Get from auth
    )
    
    keywords = None
    if faq.keywords:
        try:
            keywords = json.loads(faq.keywords)
        except:
            keywords = None
    
    return FAQResponse(
        id=faq.id,
        question=faq.question,
        answer=faq.answer,
        category=faq.category,
        keywords=keywords,
        priority=faq.priority,
        is_active=faq.is_active,
        use_count=faq.use_count,
        created_at=faq.created_at.isoformat() if faq.created_at else "",
        updated_at=faq.updated_at.isoformat() if faq.updated_at else "",
    )


@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: int,
    faq_data: FAQUpdateRequest,
    db: Session = Depends(get_db_session),
):
    """Update FAQ item."""
    faq = FAQService.update_faq(
        db=db,
        faq_id=faq_id,
        question=faq_data.question,
        answer=faq_data.answer,
        category=faq_data.category,
        keywords=faq_data.keywords,
        priority=faq_data.priority,
        is_active=faq_data.is_active,
        updated_by=None,  # TODO: Get from auth
    )
    
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    
    keywords = None
    if faq.keywords:
        try:
            keywords = json.loads(faq.keywords)
        except:
            keywords = None
    
    return FAQResponse(
        id=faq.id,
        question=faq.question,
        answer=faq.answer,
        category=faq.category,
        keywords=keywords,
        priority=faq.priority,
        is_active=faq.is_active,
        use_count=faq.use_count,
        created_at=faq.created_at.isoformat() if faq.created_at else "",
        updated_at=faq.updated_at.isoformat() if faq.updated_at else "",
    )


@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db_session),
):
    """Delete FAQ item."""
    success = FAQService.delete_faq(db, faq_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    return None


@router.post("/search", response_model=List[FAQResponse])
async def search_faq(
    search_data: FAQSearchRequest,
    db: Session = Depends(get_db_session),
):
    """Search FAQ by query."""
    faq_items = FAQService.search_faq(
        db=db,
        query=search_data.query,
        category=search_data.category,
        limit=search_data.limit
    )
    
    result = []
    for faq in faq_items:
        keywords = None
        if faq.keywords:
            try:
                keywords = json.loads(faq.keywords)
            except:
                keywords = None
        
        result.append(FAQResponse(
            id=faq.id,
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            keywords=keywords,
            priority=faq.priority,
            is_active=faq.is_active,
            use_count=faq.use_count,
            created_at=faq.created_at.isoformat() if faq.created_at else "",
            updated_at=faq.updated_at.isoformat() if faq.updated_at else "",
        ))
    
    return result


@router.post("/ai-answer")
async def get_ai_answer(
    search_data: FAQSearchRequest,
    db: Session = Depends(get_db_session),
):
    """Get AI-generated answer for a question using FAQ as context."""
    answer = await FAQService.get_ai_answer(db, search_data.query)
    
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не найдено подходящих ответов. Попробуйте переформулировать вопрос."
        )
    
    return {"answer": answer, "query": search_data.query}


