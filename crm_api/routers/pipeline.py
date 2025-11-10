"""Pipeline router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from database.db import get_db_session
from database.models_crm import PipelineStage, ClientPipeline, User
from database.models import Client
from crm_api.dependencies import get_current_user
from datetime import datetime

router = APIRouter()


class PipelineStageResponse(BaseModel):
    id: int
    name: str
    order: int
    color: str
    description: str | None
    is_active: bool

    class Config:
        from_attributes = True


class MoveClientRequest(BaseModel):
    stage_id: int
    notes: str | None = None


@router.get("/stages", response_model=List[PipelineStageResponse])
async def get_pipeline_stages(
    include_inactive: bool = Query(False, description="Include inactive stages"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get all pipeline stages."""
    query = db.query(PipelineStage)
    if not include_inactive:
        query = query.filter(PipelineStage.is_active == True)
    stages = query.order_by(PipelineStage.order).all()
    return stages


@router.post("/stages", response_model=PipelineStageResponse)
async def create_pipeline_stage(
    stage_data: dict,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create new pipeline stage."""
    stage = PipelineStage(**stage_data)
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


@router.put("/stages/{stage_id}", response_model=PipelineStageResponse)
async def update_pipeline_stage(
    stage_id: int,
    stage_data: dict,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update pipeline stage."""
    stage = db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")
    
    # Update allowed fields
    allowed_fields = ["name", "order", "color", "description", "is_active"]
    for field, value in stage_data.items():
        if field in allowed_fields and hasattr(stage, field):
            setattr(stage, field, value)
    
    db.commit()
    db.refresh(stage)
    return stage


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_stage(
    stage_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete pipeline stage."""
    stage = db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")
    
    # Check if there are clients on this stage
    clients_count = db.query(Client).filter(Client.pipeline_stage_id == stage_id).count()
    if clients_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete stage with {clients_count} clients. Move clients first."
        )
    
    db.delete(stage)
    db.commit()
    return None


@router.get("/clients/{client_id}/history")
async def get_client_pipeline_history(
    client_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get client's pipeline movement history."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    history = db.query(ClientPipeline).filter(
        ClientPipeline.client_id == client_id
    ).order_by(ClientPipeline.moved_at.desc()).all()
    
    result = []
    for entry in history:
        stage = db.query(PipelineStage).filter(PipelineStage.id == entry.stage_id).first()
        result.append({
            "id": entry.id,
            "stage_id": entry.stage_id,
            "stage_name": stage.name if stage else "Unknown",
            "stage_color": stage.color if stage else "#000000",
            "moved_at": entry.moved_at.isoformat() if entry.moved_at else None,
            "moved_by": entry.moved_by,
            "notes": entry.notes,
        })
    
    return result


@router.post("/clients/{client_id}/move-stage")
async def move_client_to_stage(
    client_id: int,
    request: MoveClientRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Move client to different pipeline stage."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    stage = db.query(PipelineStage).filter(PipelineStage.id == request.stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")
    
    # Update client's current stage
    client.pipeline_stage_id = request.stage_id
    
    # Create pipeline history entry
    pipeline_entry = ClientPipeline(
        client_id=client_id,
        stage_id=request.stage_id,
        moved_by=current_user.id,
        notes=request.notes,
        moved_at=datetime.utcnow()
    )
    db.add(pipeline_entry)
    db.commit()
    
    return {"message": "Client moved to stage successfully", "stage_id": request.stage_id}

