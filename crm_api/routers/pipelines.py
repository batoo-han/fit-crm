from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from database.db import get_db_session
from database.models_crm import SalesPipeline, PipelineStage, ClientPipeline
from crm_api.dependencies import get_current_user
from database.models_crm import User
import json

router = APIRouter()


class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_enabled: bool = True
    params: Optional[dict] = None


class PipelineResponse(PipelineBase):
    id: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[PipelineResponse])
async def list_pipelines(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    pipelines = db.query(SalesPipeline).order_by(SalesPipeline.created_at.desc()).all()
    result = []
    for p in pipelines:
        item = PipelineResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            is_enabled=p.is_enabled,
            params=json.loads(p.params) if p.params else None,
        )
        result.append(item)
    return result


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    payload: PipelineBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    exists = db.query(SalesPipeline).filter(SalesPipeline.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Pipeline with this name already exists")
    pipeline = SalesPipeline(
        name=payload.name,
        description=payload.description,
        is_enabled=payload.is_enabled,
        params=json.dumps(payload.params, ensure_ascii=False) if payload.params else None,
        created_by=current_user.id if current_user else None,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        is_enabled=pipeline.is_enabled,
        params=payload.params,
    )


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: int,
    payload: PipelineBase,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    pipeline = db.query(SalesPipeline).filter(SalesPipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    pipeline.name = payload.name
    pipeline.description = payload.description
    pipeline.is_enabled = payload.is_enabled
    pipeline.params = json.dumps(payload.params, ensure_ascii=False) if payload.params else None
    pipeline.updated_by = current_user.id if current_user else None
    db.commit()
    db.refresh(pipeline)
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        is_enabled=pipeline.is_enabled,
        params=payload.params,
    )


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    pipeline = db.query(SalesPipeline).filter(SalesPipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    # Safety: prevent delete if stages or client bindings exist
    has_stage = db.query(PipelineStage).filter(PipelineStage.pipeline_id == pipeline_id).first()
    has_client = db.query(ClientPipeline).filter(ClientPipeline.pipeline_id == pipeline_id).first()
    if has_stage or has_client:
        raise HTTPException(status_code=400, detail="Pipeline has stages or client history; disable instead of delete")
    db.delete(pipeline)
    db.commit()
    return


