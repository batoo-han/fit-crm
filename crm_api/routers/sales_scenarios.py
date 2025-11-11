"""Sales scenarios router for managing sales scenarios."""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database.db import get_db_session
from database.models_crm import SalesScenario
from database.models import Client
from services.sales_scenario_service import SalesScenarioService
from loguru import logger
import json

router = APIRouter()


class SalesScenarioResponse(BaseModel):
    """Sales scenario response model."""
    id: int
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_conditions: Optional[Dict[str, Any]]
    message_template: str
    action_type: Optional[str]
    is_active: bool
    priority: int
    use_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SalesScenarioCreateRequest(BaseModel):
    """Sales scenario create request model."""
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_conditions: Optional[Dict[str, Any]] = None
    message_template: str
    action_type: Optional[str] = None
    priority: int = 0


class SalesScenarioUpdateRequest(BaseModel):
    """Sales scenario update request model."""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    message_template: Optional[str] = None
    action_type: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class GenerateMessageRequest(BaseModel):
    """Generate personalized message request."""
    client_id: int
    scenario_id: Optional[int] = None  # If not provided, will use best matching scenario


@router.get("", response_model=List[SalesScenarioResponse])
async def get_scenarios(
    trigger_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db_session),
):
    """Get all sales scenarios, optionally filtered."""
    scenarios = SalesScenarioService.get_all_scenarios(
        db, trigger_type=trigger_type, is_active=is_active
    )
    
    result = []
    for scenario in scenarios:
        conditions = None
        if scenario.trigger_conditions:
            try:
                conditions = json.loads(scenario.trigger_conditions)
            except:
                conditions = None
        
        result.append(SalesScenarioResponse(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            trigger_type=scenario.trigger_type,
            trigger_conditions=conditions,
            message_template=scenario.message_template,
            action_type=scenario.action_type,
            is_active=scenario.is_active,
            priority=scenario.priority,
            use_count=scenario.use_count,
            created_at=scenario.created_at.isoformat() if scenario.created_at else "",
            updated_at=scenario.updated_at.isoformat() if scenario.updated_at else "",
        ))
    
    return result


@router.get("/{scenario_id}", response_model=SalesScenarioResponse)
async def get_scenario_by_id(
    scenario_id: int,
    db: Session = Depends(get_db_session),
):
    """Get sales scenario by ID."""
    scenario = SalesScenarioService.get_scenario_by_id(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    
    conditions = None
    if scenario.trigger_conditions:
        try:
            conditions = json.loads(scenario.trigger_conditions)
        except:
            conditions = None
    
    return SalesScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        trigger_type=scenario.trigger_type,
        trigger_conditions=conditions,
        message_template=scenario.message_template,
        action_type=scenario.action_type,
        is_active=scenario.is_active,
        priority=scenario.priority,
        use_count=scenario.use_count,
        created_at=scenario.created_at.isoformat() if scenario.created_at else "",
        updated_at=scenario.updated_at.isoformat() if scenario.updated_at else "",
    )


@router.post("", response_model=SalesScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    scenario_data: SalesScenarioCreateRequest,
    db: Session = Depends(get_db_session),
):
    """Create new sales scenario."""
    scenario = SalesScenarioService.create_scenario(
        db=db,
        name=scenario_data.name,
        description=scenario_data.description,
        trigger_type=scenario_data.trigger_type,
        trigger_conditions=scenario_data.trigger_conditions,
        message_template=scenario_data.message_template,
        action_type=scenario_data.action_type,
        priority=scenario_data.priority,
        created_by=None,  # TODO: Get from auth
    )
    
    conditions = None
    if scenario.trigger_conditions:
        try:
            conditions = json.loads(scenario.trigger_conditions)
        except:
            conditions = None
    
    return SalesScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        trigger_type=scenario.trigger_type,
        trigger_conditions=conditions,
        message_template=scenario.message_template,
        action_type=scenario.action_type,
        is_active=scenario.is_active,
        priority=scenario.priority,
        use_count=scenario.use_count,
        created_at=scenario.created_at.isoformat() if scenario.created_at else "",
        updated_at=scenario.updated_at.isoformat() if scenario.updated_at else "",
    )


@router.put("/{scenario_id}", response_model=SalesScenarioResponse)
async def update_scenario(
    scenario_id: int,
    scenario_data: SalesScenarioUpdateRequest,
    db: Session = Depends(get_db_session),
):
    """Update sales scenario."""
    scenario = SalesScenarioService.update_scenario(
        db=db,
        scenario_id=scenario_id,
        name=scenario_data.name,
        description=scenario_data.description,
        trigger_type=scenario_data.trigger_type,
        trigger_conditions=scenario_data.trigger_conditions,
        message_template=scenario_data.message_template,
        action_type=scenario_data.action_type,
        priority=scenario_data.priority,
        is_active=scenario_data.is_active,
        updated_by=None,  # TODO: Get from auth
    )
    
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    
    conditions = None
    if scenario.trigger_conditions:
        try:
            conditions = json.loads(scenario.trigger_conditions)
        except:
            conditions = None
    
    return SalesScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        trigger_type=scenario.trigger_type,
        trigger_conditions=conditions,
        message_template=scenario.message_template,
        action_type=scenario.action_type,
        is_active=scenario.is_active,
        priority=scenario.priority,
        use_count=scenario.use_count,
        created_at=scenario.created_at.isoformat() if scenario.created_at else "",
        updated_at=scenario.updated_at.isoformat() if scenario.updated_at else "",
    )


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db_session),
):
    """Delete sales scenario."""
    success = SalesScenarioService.delete_scenario(db, scenario_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return None


@router.post("/generate-message")
async def generate_personalized_message(
    request: GenerateMessageRequest,
    db: Session = Depends(get_db_session),
):
    """Generate personalized message for client using sales scenario."""
    client = db.query(Client).filter(Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    if request.scenario_id:
        # Use specific scenario
        scenario = SalesScenarioService.get_scenario_by_id(db, request.scenario_id)
        if not scenario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        
        message = await SalesScenarioService.generate_personalized_message(db, scenario, client)
        return {
            "message": message,
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "action_type": scenario.action_type
        }
    else:
        # Use best matching scenario
        recommendations = await SalesScenarioService.get_recommendations(db, client)
        if not recommendations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Не найдено подходящих сценариев для клиента"
            )
        
        return {
            "message": recommendations[0]["message"],
            "scenario_id": recommendations[0]["scenario_id"],
            "scenario_name": recommendations[0]["name"],
            "action_type": recommendations[0]["action_type"],
            "recommendations": recommendations
        }


@router.get("/client/{client_id}/recommendations")
async def get_client_recommendations(
    client_id: int,
    db: Session = Depends(get_db_session),
):
    """Get personalized recommendations for client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    recommendations = await SalesScenarioService.get_recommendations(db, client)
    return {"recommendations": recommendations}


