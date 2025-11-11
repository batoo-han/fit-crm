"""Service for sales scenarios and personalized recommendations."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger
import json
from datetime import datetime
from database.models_crm import SalesScenario, ClientAction, ActionType, PipelineStage
from database.models import Client
from services.ai_service import ai_service


class SalesScenarioService:
    """Service for managing sales scenarios and generating personalized offers."""
    
    @staticmethod
    def get_matching_scenarios(
        db: Session,
        client: Client,
        trigger_type: Optional[str] = None
    ) -> List[SalesScenario]:
        """
        Get matching sales scenarios for a client.
        
        Args:
            db: Database session
            client: Client object
            trigger_type: Optional trigger type filter
            
        Returns:
            List of matching scenarios sorted by priority
        """
        query = db.query(SalesScenario).filter(SalesScenario.is_active == True)
        
        if trigger_type:
            query = query.filter(SalesScenario.trigger_type == trigger_type)
        
        scenarios = query.order_by(SalesScenario.priority.desc()).all()
        
        # Filter scenarios by trigger conditions
        matching_scenarios = []
        for scenario in scenarios:
            if SalesScenarioService._check_trigger_conditions(db, scenario, client):
                matching_scenarios.append(scenario)
        
        return matching_scenarios
    
    @staticmethod
    def _check_trigger_conditions(
        db: Session,
        scenario: SalesScenario,
        client: Client
    ) -> bool:
        """Check if scenario trigger conditions match client."""
        if not scenario.trigger_conditions:
            return True
        
        try:
            conditions = json.loads(scenario.trigger_conditions)
        except:
            return True
        
        # Check pipeline stage
        if "pipeline_stage" in conditions:
            stage_name = conditions["pipeline_stage"]
            if client.pipeline_stage_id:
                stage = db.query(PipelineStage).filter(PipelineStage.id == client.pipeline_stage_id).first()
                if not stage or stage.name != stage_name:
                    return False
        
        # Check client status
        if "client_status" in conditions:
            if client.status != conditions["client_status"]:
                return False
        
        # Check age range
        if "age_min" in conditions and client.age:
            if client.age < conditions["age_min"]:
                return False
        if "age_max" in conditions and client.age:
            if client.age > conditions["age_max"]:
                return False
        
        # Check gender
        if "gender" in conditions:
            if client.gender != conditions["gender"]:
                return False
        
        # Check experience level
        if "experience_level" in conditions:
            if client.experience_level != conditions["experience_level"]:
                return False
        
        # Check fitness goals
        if "fitness_goals" in conditions:
            goals = conditions["fitness_goals"]
            if isinstance(goals, list):
                if not client.fitness_goals or not any(goal in client.fitness_goals for goal in goals):
                    return False
            elif client.fitness_goals != goals:
                return False
        
        # Check if client has free program
        if "has_free_program" in conditions:
            from handlers.start import has_free_program
            has_free = has_free_program(client.id)
            if has_free != conditions["has_free_program"]:
                return False
        
        return True
    
    @staticmethod
    async def generate_personalized_message(
        db: Session,
        scenario: SalesScenario,
        client: Client
    ) -> str:
        """
        Generate personalized sales message from scenario template.
        
        Args:
            db: Database session
            scenario: Sales scenario
            client: Client object
            
        Returns:
            Personalized message
        """
        # Build client context
        context = {
            "name": client.first_name or "Клиент",
            "age": client.age,
            "gender": client.gender,
            "experience_level": client.experience_level,
            "fitness_goals": client.fitness_goals,
            "height": client.height,
            "weight": client.weight,
            "bmi": client.bmi,
        }
        
        # Get pipeline stage
        if client.pipeline_stage_id:
            stage = db.query(PipelineStage).filter(PipelineStage.id == client.pipeline_stage_id).first()
            if stage:
                context["pipeline_stage"] = stage.name
        
        # Build system prompt
        system_prompt = """Ты - AI-ассистент фитнес-тренера. Твоя задача - генерировать персонализированные сообщения для клиентов на основе шаблона и данных клиента.

Используй шаблон сообщения как основу, но адаптируй его под конкретного клиента, используя его данные (имя, возраст, цели, опыт и т.д.).

Будь дружелюбным, профессиональным и мотивирующим. Используй эмодзи умеренно."""
        
        # Build user prompt
        user_prompt = f"""Шаблон сообщения:
{scenario.message_template}

Данные клиента:
{json.dumps(context, ensure_ascii=False, indent=2)}

Сгенерируй персонализированное сообщение для клиента на основе шаблона и его данных. Адаптируй сообщение под клиента, но сохрани основную суть и структуру шаблона."""
        
        try:
            # Generate personalized message
            message = await ai_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.8
            )
            
            # Increment use count
            scenario.use_count += 1
            db.commit()
            
            return message
        except Exception as e:
            logger.error(f"Error generating personalized message: {e}")
            # Fallback to template with simple replacements
            message = scenario.message_template
            if context["name"]:
                message = message.replace("{name}", context["name"])
            return message
    
    @staticmethod
    async def get_recommendations(
        db: Session,
        client: Client
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for client.
        
        Args:
            db: Database session
            client: Client object
            
        Returns:
            List of recommendations with messages and actions
        """
        recommendations = []
        
        # Get matching scenarios
        scenarios = SalesScenarioService.get_matching_scenarios(db, client)
        
        for scenario in scenarios:
            try:
                message = await SalesScenarioService.generate_personalized_message(db, scenario, client)
                recommendations.append({
                    "scenario_id": scenario.id,
                    "name": scenario.name,
                    "message": message,
                    "action_type": scenario.action_type,
                    "priority": scenario.priority
                })
            except Exception as e:
                logger.error(f"Error generating recommendation for scenario {scenario.id}: {e}")
        
        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"], reverse=True)
        
        return recommendations
    
    @staticmethod
    def get_scenario_by_id(db: Session, scenario_id: int) -> Optional[SalesScenario]:
        """Get sales scenario by ID."""
        return db.query(SalesScenario).filter(SalesScenario.id == scenario_id).first()
    
    @staticmethod
    def get_all_scenarios(
        db: Session,
        trigger_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[SalesScenario]:
        """Get all sales scenarios, optionally filtered."""
        query = db.query(SalesScenario)
        
        if trigger_type:
            query = query.filter(SalesScenario.trigger_type == trigger_type)
        if is_active is not None:
            query = query.filter(SalesScenario.is_active == is_active)
        
        return query.order_by(SalesScenario.priority.desc(), SalesScenario.name).all()
    
    @staticmethod
    def create_scenario(
        db: Session,
        name: str,
        message_template: str,
        trigger_type: str,
        trigger_conditions: Optional[Dict[str, Any]] = None,
        action_type: Optional[str] = None,
        description: Optional[str] = None,
        priority: int = 0,
        created_by: Optional[int] = None
    ) -> SalesScenario:
        """Create new sales scenario."""
        scenario = SalesScenario(
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_conditions=json.dumps(trigger_conditions) if trigger_conditions else None,
            message_template=message_template,
            action_type=action_type,
            is_active=True,
            priority=priority,
            created_by=created_by
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        logger.info(f"Created sales scenario {scenario.id}: {name}")
        return scenario
    
    @staticmethod
    def update_scenario(
        db: Session,
        scenario_id: int,
        name: Optional[str] = None,
        message_template: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_conditions: Optional[Dict[str, Any]] = None,
        action_type: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[int] = None
    ) -> Optional[SalesScenario]:
        """Update sales scenario."""
        scenario = db.query(SalesScenario).filter(SalesScenario.id == scenario_id).first()
        if not scenario:
            return None
        
        if name is not None:
            scenario.name = name
        if message_template is not None:
            scenario.message_template = message_template
        if trigger_type is not None:
            scenario.trigger_type = trigger_type
        if trigger_conditions is not None:
            scenario.trigger_conditions = json.dumps(trigger_conditions) if trigger_conditions else None
        if action_type is not None:
            scenario.action_type = action_type
        if description is not None:
            scenario.description = description
        if priority is not None:
            scenario.priority = priority
        if is_active is not None:
            scenario.is_active = is_active
        if updated_by is not None:
            scenario.updated_by = updated_by
        
        db.commit()
        db.refresh(scenario)
        logger.info(f"Updated sales scenario {scenario_id}")
        return scenario
    
    @staticmethod
    def delete_scenario(db: Session, scenario_id: int) -> bool:
        """Delete sales scenario."""
        scenario = db.query(SalesScenario).filter(SalesScenario.id == scenario_id).first()
        if not scenario:
            return False
        
        db.delete(scenario)
        db.commit()
        logger.info(f"Deleted sales scenario {scenario_id}")
        return True


