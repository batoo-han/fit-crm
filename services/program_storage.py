"""Service for storing generated training programs."""
from database.db import get_db_session
from database.models import TrainingProgram, Client
from typing import Optional, Dict, Any
from loguru import logger
import json


class ProgramStorage:
    """Store and retrieve training programs."""
    
    @staticmethod
    def save_program(
        client_id: int,
        program_data: Dict[str, Any],
        program_type: str = "free_demo",
        pdf_path: Optional[str] = None,
        formatted_program: Optional[str] = None
    ) -> Optional[int]:
        """
        Save generated program to database.
        
        Args:
            client_id: Client ID
            program_data: Program data from generator
            program_type: Type of program (free_demo, paid_monthly, paid_3month)
            pdf_path: Path to generated PDF file
        
        Returns:
            Program ID or None
        """
        db = get_db_session()
        try:
            # Обрезаем бесплатную программу до 1-й недели
            if program_type == "free_demo" and isinstance(program_data, dict):
                try:
                    weeks = program_data.get("weeks")
                    if isinstance(weeks, dict) and len(weeks) > 0:
                        # Определяем минимальный номер недели и оставляем только её
                        week_numbers = [int(k) for k in weeks.keys() if str(k).isdigit()]
                        if not week_numbers:
                            # Если ключи не числовые, попробуем взять первый ключ по сортировке
                            first_key = sorted(weeks.keys(), key=lambda x: str(x))[0]
                            program_data["weeks"] = {first_key: weeks[first_key]}
                        else:
                            first_week = min(week_numbers)
                            program_data["weeks"] = {first_week: weeks.get(first_week) or weeks.get(str(first_week))}
                        # При наличии агрегатов/метаданных можно также обрезать сопутствующие структуры при необходимости
                except Exception as _:
                    # В случае любой ошибки в обрезке — продолжаем сохранение исходных данных
                    pass

            program = TrainingProgram(
                client_id=client_id,
                program_type=program_type,
                program_data=json.dumps(program_data, ensure_ascii=False),
                formatted_program=formatted_program,
                is_paid=(program_type in ["paid_monthly", "paid_3month"])
            )
            db.add(program)
            db.commit()
            
            # Update client's current program
            client = db.query(Client).filter(Client.id == client_id).first()
            if client:
                client.current_program_id = program.id
                db.commit()
            
            logger.info(f"Program saved: ID {program.id} for client {client_id}")
            return program.id
            
        except Exception as e:
            logger.error(f"Error saving program: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    @staticmethod
    def get_program(program_id: int) -> Optional[Dict[str, Any]]:
        """
        Get program by ID.
        
        Args:
            program_id: Program ID
        
        Returns:
            Program data or None
        """
        db = get_db_session()
        try:
            program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
            if program:
                return json.loads(program.program_data)
            return None
        except Exception as e:
            logger.error(f"Error getting program: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def get_client_programs(client_id: int) -> list:
        """
        Get all programs for client.
        
        Args:
            client_id: Client ID
        
        Returns:
            List of program data
        """
        db = get_db_session()
        try:
            programs = db.query(TrainingProgram).filter(
                TrainingProgram.client_id == client_id
            ).order_by(TrainingProgram.created_at.desc()).all()
            
            result = []
            for program in programs:
                try:
                    data = json.loads(program.program_data)
                    result.append({
                        "id": program.id,
                        "type": program.program_type,
                        "data": data,
                        "created_at": program.created_at.isoformat(),
                        "is_completed": program.is_completed
                    })
                except:
                    continue
            
            return result
        except Exception as e:
            logger.error(f"Error getting client programs: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def mark_program_completed(program_id: int) -> bool:
        """
        Mark program as completed.
        
        Args:
            program_id: Program ID
        
        Returns:
            True if successful
        """
        db = get_db_session()
        try:
            program = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
            if program:
                program.is_completed = True
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking program completed: {e}")
            db.rollback()
            return False
        finally:
            db.close()
