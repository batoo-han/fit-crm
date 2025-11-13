"""Service for cleaning up training programs."""
from database.db import get_db_session
from database.models import TrainingProgram, Client
from database.models_crm import ProgramHistory
from sqlalchemy import and_, or_
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import json


class ProgramCleanupService:
    """Service for cleaning up and archiving training programs."""
    
    @staticmethod
    def cleanup_programs(
        days_old: int = 30,
        archive_sent: bool = True,
        delete_unsent: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up training programs.
        
        Args:
            days_old: Programs older than this many days will be processed
            archive_sent: Whether to archive programs that were sent to clients
            delete_unsent: Whether to delete programs that were never sent
            dry_run: If True, only report what would be done without making changes
        
        Returns:
            Dict with cleanup statistics
        """
        db = next(get_db_session())
        stats = {
            "archived": 0,
            "deleted": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find programs older than cutoff_date
            old_programs = db.query(TrainingProgram).filter(
                TrainingProgram.created_at < cutoff_date
            ).all()
            
            logger.info(f"Found {len(old_programs)} programs older than {days_old} days")
            
            for program in old_programs:
                try:
                    # Check if program is still attached to an active client
                    client = db.query(Client).filter(Client.id == program.client_id).first()
                    
                    if not client:
                        # Client was deleted, program should be archived or deleted
                        if archive_sent and program.sent_at:
                            if not dry_run:
                                ProgramCleanupService._archive_program(program, db, None)
                            stats["archived"] += 1
                            logger.info(f"Archived program {program.id} (client deleted, was sent)")
                        elif delete_unsent and not program.sent_at:
                            if not dry_run:
                                db.delete(program)
                            stats["deleted"] += 1
                            logger.info(f"Deleted program {program.id} (client deleted, never sent)")
                        else:
                            stats["skipped"] += 1
                        continue
                    
                    # Program is attached to an active client
                    # Не удаляем программы, которые привязаны к клиентам, даже если они не были отправлены
                    # Они могут быть нужны для истории или восстановления
                    if program.sent_at:
                        # Program was sent - archive it but keep reference in history
                        if archive_sent:
                            if not dry_run:
                                ProgramCleanupService._archive_program(program, db, None)
                            stats["archived"] += 1
                            logger.info(f"Archived program {program.id} (was sent to client {client.id})")
                        else:
                            stats["skipped"] += 1
                    else:
                        # Program was never sent but is attached to client - skip it
                        # Не удаляем программы, привязанные к клиентам, даже если они не были отправлены
                        stats["skipped"] += 1
                        logger.info(f"Skipped program {program.id} (attached to client {client.id}, never sent)")
                            
                except Exception as e:
                    error_msg = f"Error processing program {program.id}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            if not dry_run:
                db.commit()
                logger.info(f"Cleanup completed: {stats['archived']} archived, {stats['deleted']} deleted, {stats['skipped']} skipped")
            else:
                logger.info(f"Dry run completed: would archive {stats['archived']}, delete {stats['deleted']}, skip {stats['skipped']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in cleanup_programs: {e}")
            db.rollback()
            stats["errors"].append(str(e))
            return stats
        finally:
            db.close()
    
    @staticmethod
    def _archive_program(program: TrainingProgram, db, archived_by: Optional[int] = None):
        """Archive a program to history."""
        try:
            history_entry = ProgramHistory(
                original_program_id=program.id,
                client_id=program.client_id,
                program_type=program.program_type,
                program_data=program.program_data,
                formatted_program=program.formatted_program,
                sent_at=program.sent_at or datetime.utcnow(),
                archived_at=datetime.utcnow(),
                archived_by=archived_by,
                notes=f"Архивировано автоматически при очистке"
            )
            db.add(history_entry)
            # Delete original program after archiving
            db.delete(program)
        except Exception as e:
            logger.error(f"Error archiving program {program.id}: {e}")
            raise

