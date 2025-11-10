"""Integration service for CRM system."""
from database.db import get_db_session
from database.models import Client, TrainingProgram, Payment
from database.models_crm import (
    PipelineStage, ClientPipeline, ClientAction, 
    ActionType, ProgressJournal
)
from loguru import logger
from datetime import datetime
import json


class CRMIntegration:
    """Service for integrating bot with CRM system."""
    
    @staticmethod
    def create_client_in_crm(telegram_id: int, client_data: dict = None) -> int | None:
        """
        Create or update client in CRM when created in bot.
        
        Returns:
            Client ID or None
        """
        db = get_db_session()
        try:
            client = db.query(Client).filter(Client.telegram_id == telegram_id).first()
            if not client:
                logger.warning(f"Client with telegram_id {telegram_id} not found")
                return None
            
            # Get "Первичный контакт" stage
            initial_stage = db.query(PipelineStage).filter(
                PipelineStage.name == "Первичный контакт"
            ).first()
            
            if initial_stage and not client.pipeline_stage_id:
                client.pipeline_stage_id = initial_stage.id
                
                # Create pipeline history entry
                pipeline_entry = ClientPipeline(
                    client_id=client.id,
                    stage_id=initial_stage.id,
                    moved_at=datetime.utcnow(),
                    notes="Автоматически создан из Telegram бота"
                )
                db.add(pipeline_entry)
                
                # Create action
                action = ClientAction(
                    client_id=client.id,
                    action_type=ActionType.MESSAGE.value,
                    action_date=datetime.utcnow(),
                    description="Клиент начал взаимодействие с ботом",
                )
                db.add(action)
                
                db.commit()
                logger.info(f"Client {client.id} added to CRM pipeline")
            
            return client.id
            
        except Exception as e:
            logger.error(f"Error creating client in CRM: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    @staticmethod
    def move_client_to_stage_by_name(client_id: int, stage_name: str, notes: str = None):
        """
        Move client to pipeline stage by stage name.
        
        Args:
            client_id: Client ID
            stage_name: Name of the pipeline stage
            notes: Optional notes for the move
        """
        db = get_db_session()
        try:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                logger.warning(f"Client {client_id} not found")
                return False
            
            # Get stage by name
            stage = db.query(PipelineStage).filter(
                PipelineStage.name == stage_name,
                PipelineStage.is_active == True
            ).first()
            
            if not stage:
                logger.warning(f"Pipeline stage '{stage_name}' not found")
                return False
            
            # Don't move if already on this stage
            if client.pipeline_stage_id == stage.id:
                return True
            
            old_stage_id = client.pipeline_stage_id
            client.pipeline_stage_id = stage.id
            
            # Create pipeline history entry
            pipeline_entry = ClientPipeline(
                client_id=client_id,
                stage_id=stage.id,
                moved_at=datetime.utcnow(),
                notes=notes or f"Автоматическое перемещение в этап '{stage_name}'"
            )
            db.add(pipeline_entry)
            
            db.commit()
            logger.info(f"Client {client_id} moved to stage '{stage_name}' (from stage {old_stage_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error moving client to stage: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def move_client_to_qualified_stage(client_id: int):
        """Move client to 'Консультация' stage after completing questionnaire."""
        return CRMIntegration.move_client_to_stage_by_name(
            client_id=client_id,
            stage_name="Консультация",
            notes="Клиент прошел опросник и получил бесплатную программу"
        )
    
    @staticmethod
    def move_client_to_paid_stage(client_id: int, payment_id: int = None):
        """Move client to 'Куплена услуга' stage after payment."""
        db = get_db_session()
        try:
            # Use the new method
            success = CRMIntegration.move_client_to_stage_by_name(
                client_id=client_id,
                stage_name="Куплена услуга",
                notes=f"Оплата получена (payment_id: {payment_id})" if payment_id else "Оплата получена"
            )
            
            if success:
                # Create action (need new session as move_client_to_stage_by_name closes its session)
                db = get_db_session()
                try:
                    action = ClientAction(
                        client_id=client_id,
                        action_type=ActionType.PAYMENT_RECEIVED.value,
                        action_date=datetime.utcnow(),
                        description=f"Получена оплата (payment_id: {payment_id})" if payment_id else "Получена оплата",
                    )
                    db.add(action)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error creating payment action: {e}")
                    db.rollback()
                finally:
                    db.close()
            
        except Exception as e:
            logger.error(f"Error moving client to paid stage: {e}")
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def save_paid_program(
        client_id: int,
        program_data: dict,
        formatted_program: str,
        program_type: str = "paid_monthly"
    ) -> int | None:
        """
        Save paid training program to database.
        
        Args:
            client_id: Client ID
            program_data: Program data from generator
            formatted_program: Formatted program text for display
            program_type: Type of program (paid_monthly, paid_3month)
        
        Returns:
            Program ID or None
        """
        db = get_db_session()
        try:
            program = TrainingProgram(
                client_id=client_id,
                program_type=program_type,
                program_data=json.dumps(program_data, ensure_ascii=False),
                formatted_program=formatted_program,
                is_paid=True,
                assigned_at=datetime.utcnow()
            )
            db.add(program)
            db.commit()
            
            # Update client's current program
            client = db.query(Client).filter(Client.id == client_id).first()
            if client:
                client.current_program_id = program.id
                client.status = "client"
                db.commit()
                
                # Move to "Активный клиент" stage (creates its own session)
                CRMIntegration.move_client_to_stage_by_name(
                    client_id=client_id,
                    stage_name="Активный клиент",
                    notes="Программа выдана клиенту"
                )
                
                # Create action (need new session)
                db = get_db_session()
                try:
                    action = ClientAction(
                        client_id=client_id,
                        action_type=ActionType.PROGRAM_ASSIGNED.value,
                        action_date=datetime.utcnow(),
                        description=f"Назначена программа тренировок (program_id: {program.id})",
                    )
                    db.add(action)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error creating program action: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            logger.info(f"Paid program saved: ID {program.id} for client {client_id}")
            return program.id
            
        except Exception as e:
            logger.error(f"Error saving paid program: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    @staticmethod
    def create_progress_entry(
        client_id: int,
        program_id: int | None,
        period: str,
        measurements: dict
    ) -> int | None:
        """
        Create progress journal entry.
        
        Args:
            client_id: Client ID
            program_id: Program ID (optional)
            period: Period (before, week_1, week_2, etc.)
            measurements: Dictionary with measurement values
        
        Returns:
            Entry ID or None
        """
        db = get_db_session()
        try:
            entry = ProgressJournal(
                client_id=client_id,
                program_id=program_id,
                period=period,
                measurement_date=datetime.utcnow(),
                **measurements
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            
            logger.info(f"Progress entry created: ID {entry.id} for client {client_id}")
            return entry.id
            
        except Exception as e:
            logger.error(f"Error creating progress entry: {e}")
            db.rollback()
            return None
        finally:
            db.close()

