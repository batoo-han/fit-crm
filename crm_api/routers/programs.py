"""Programs router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database.db import get_db_session
from database.models import TrainingProgram, Client, ProgramVersion
from database.models_crm import User
from crm_api.dependencies import get_current_user
import json
from pydantic import BaseModel
from services.program_storage import ProgramStorage
from services.program_formatter import ProgramFormatter
from services.training_program_generator import program_generator
from loguru import logger
import shutil
from services.pdf_generator import PDFGenerator
from services.program_delivery import deliver_program_to_client

router = APIRouter()


class AutoGenerateRequest(BaseModel):
    """Request model for auto-generating full training program."""
    client_id: int
    weeks: int | None = 4
    location: str | None = None  # 'дом' | 'зал' | 'улица'


@router.post("/auto-generate", status_code=status.HTTP_201_CREATED)
async def auto_generate_program(
    payload: AutoGenerateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-generate a full personalized training program for a client.
    Uses stored client profile (age, gender, experience, goals, location) and generator.
    """
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # Prepare generator inputs
    gender = "male" if (client.gender or "").lower().startswith("м") else "female"
    age = client.age or 30
    # Map experience to expected codes
    exp_raw = (client.experience_level or "").lower()
    if "нов" in exp_raw or "begin" in exp_raw:
        experience = "beginner"
    elif "прод" in exp_raw or "adv" in exp_raw:
        experience = "advanced"
    else:
        experience = "intermediate"
    # Map goals
    goals_raw = (client.fitness_goals or "").lower()
    if "похуд" in goals_raw or "вес" in goals_raw:
        goal_code = "weight_loss"
    elif "мас" in goals_raw:
        goal_code = "muscle"
    elif "вынос" in goals_raw or "endurance" in goals_raw:
        goal_code = "endurance"
    else:
        goal_code = "general"
    # Location
    location = payload.location or client.location or "дом"

    try:
        # Get base program data (multi-week) from generator
        program_data = await program_generator.get_program_from_sheets(
            gender=gender,
            age=age,
            experience=experience,
            goal=goal_code,
            location=location
        )
        if not program_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate program data")

        # Limit number of weeks if requested
        if payload.weeks and isinstance(program_data, dict) and "weeks" in program_data:
            try:
                weeks_filtered = {str(wk): data for wk, data in program_data["weeks"].items() if int(wk) <= payload.weeks}
                program_data["weeks"] = weeks_filtered
            except Exception:
                pass

        # Format program text
        client_name = client.first_name or "Клиент"
        formatted_program = await ProgramFormatter.format_program(
            program_data=program_data,
            client_name=client_name
        )

        # Save program
        saved = ProgramStorage.save_program(
            client_id=client.id,
            program_data=program_data,
            program_type="auto_full",
            formatted_program=formatted_program
        )

        # Response
        return {
            "program_id": saved.id,
            "client_id": client.id,
            "program_type": saved.program_type,
            "formatted_program": saved.formatted_program,
            "created_at": saved.created_at.isoformat() if saved.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-generate error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Generation error")


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


@router.get("/{program_id}/versions")
async def list_versions(
    program_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    versions = (
        db.query(ProgramVersion)
        .filter(ProgramVersion.program_id == program_id)
        .order_by(ProgramVersion.created_at.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "created_by": v.created_by,
        }
        for v in versions
    ]


@router.post("/{program_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version_snapshot(
    program_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    snapshot = ProgramVersion(
        program_id=program.id,
        program_data=program.program_data,
        formatted_program=program.formatted_program,
        created_by=current_user.id if current_user else None,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"id": snapshot.id, "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None}


@router.post("/versions/{version_id}/restore", status_code=status.HTTP_200_OK)
async def restore_version(
    version_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    version = db.query(ProgramVersion).filter(ProgramVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    program = db.query(TrainingProgram).filter(TrainingProgram.id == version.program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    program.program_data = version.program_data
    program.formatted_program = version.formatted_program
    db.commit()
    return {"success": True}


@router.get("/{program_id}/export-pdf")
async def export_pdf(
    program_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    client = db.query(Client).filter(Client.id == program.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not program.formatted_program:
        raise HTTPException(status_code=400, detail="Program has no formatted text")
    pdf_path = PDFGenerator.generate_program_pdf(
        program_text=program.formatted_program,
        client_id=client.id,
        client_name=client.first_name or "Клиент",
    )
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="Failed to generate PDF")
    # Copy into uploads to serve statically
    os.makedirs("uploads", exist_ok=True)
    target_name = os.path.basename(pdf_path)
    target_path = os.path.join("uploads", target_name)
    shutil.copyfile(pdf_path, target_path)
    return {"url": f"/uploads/{target_name}"}


class SendProgramRequest(BaseModel):
    channels: list[str]  # ["telegram","email"]
    message: str | None = None


@router.post("/{program_id}/send")
async def send_program(
    program_id: int,
    payload: SendProgramRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    client = db.query(Client).filter(Client.id == program.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not program.formatted_program:
        raise HTTPException(status_code=400, detail="Program has no formatted text")

    # Ensure PDF
    pdf_path = PDFGenerator.generate_program_pdf(
        program_text=program.formatted_program,
        client_id=client.id,
        client_name=client.first_name or "Клиент",
    )
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

    results = {}

    results = deliver_program_to_client(
        program=program,
        client=client,
        channels=payload.channels,
        message=payload.message,
    )
    return {"results": results}

