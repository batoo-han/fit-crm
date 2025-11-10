"""Programs router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database.db import get_db_session
from database.models import TrainingProgram, Client
from database.models_crm import User
from crm_api.dependencies import get_current_user
import json

router = APIRouter()


@router.get("")
async def get_programs(
    client_id: int | None = None,
    is_paid: bool | None = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of training programs."""
    query = db.query(TrainingProgram)
    
    if client_id:
        query = query.filter(TrainingProgram.client_id == client_id)
    if is_paid is not None:
        query = query.filter(TrainingProgram.is_paid == is_paid)
    
    programs = query.order_by(TrainingProgram.created_at.desc()).all()
    
    result = []
    for program in programs:
        try:
            program_data = json.loads(program.program_data) if program.program_data else {}
        except:
            program_data = {}
        
        result.append({
            "id": program.id,
            "client_id": program.client_id,
            "program_type": program.program_type,
            "formatted_program": program.formatted_program,
            "is_paid": program.is_paid,
            "is_completed": program.is_completed,
            "created_at": program.created_at.isoformat() if program.created_at else None,
            "assigned_at": program.assigned_at.isoformat() if program.assigned_at else None,
        })
    
    return result


@router.get("/{program_id}")
async def get_program(
    program_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get program details."""
    program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    try:
        program_data = json.loads(program.program_data) if program.program_data else {}
    except:
        program_data = {}
    
    return {
        "id": program.id,
        "client_id": program.client_id,
        "program_type": program.program_type,
        "program_data": program_data,
        "formatted_program": program.formatted_program,
        "is_paid": program.is_paid,
        "is_completed": program.is_completed,
        "created_at": program.created_at.isoformat() if program.created_at else None,
        "assigned_at": program.assigned_at.isoformat() if program.assigned_at else None,
    }


@router.get("/{program_id}/view")
async def view_program_table(
    program_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """View program in table format (for CRM display)."""
    program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Return formatted program text for table display
    return {
        "id": program.id,
        "formatted_program": program.formatted_program,
        "program_type": program.program_type,
    }


@router.put("/{program_id}")
async def update_program(
    program_id: int,
    update_data: dict,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update program."""
    program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Update allowed fields
    if "formatted_program" in update_data:
        program.formatted_program = update_data["formatted_program"]
    if "is_completed" in update_data:
        program.is_completed = update_data["is_completed"]
    if "program_data" in update_data:
        # Update program_data (the structured JSON data)
        program.program_data = json.dumps(update_data["program_data"], ensure_ascii=False)
    
    db.commit()
    db.refresh(program)
    
    # Return updated program
    try:
        program_data = json.loads(program.program_data) if program.program_data else {}
    except:
        program_data = {}
    
    return {
        "id": program.id,
        "client_id": program.client_id,
        "program_type": program.program_type,
        "program_data": program_data,
        "formatted_program": program.formatted_program,
        "is_paid": program.is_paid,
        "is_completed": program.is_completed,
    }

