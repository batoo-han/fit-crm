"""Initialize CRM models and create default data."""
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db_session, engine
from database.models import Base
from database.models_crm import (
    PipelineStage, User, ClientPipeline, ClientAction, 
    ClientContact, ProgressJournal
)
from loguru import logger
import bcrypt
import os
from dotenv import load_dotenv


def create_tables():
    """Create all database tables."""
    try:
        # Import all models to register them with Base.metadata
        # This ensures all tables are created
        from database.models import Client, TrainingProgram, Payment, Lead, WebsiteContact, WebsiteSettings
        from database.models_crm import (
            PipelineStage, User, ClientPipeline, ClientAction,
            ClientContact, ProgressJournal
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        raise


def create_default_pipeline_stages():
    """Create default pipeline stages."""
    db = get_db_session()
    try:
        # Check if stages already exist
        existing = db.query(PipelineStage).count()
        if existing > 0:
            logger.info("Pipeline stages already exist, skipping creation")
            return
        
        stages = [
            {"name": "Первичный контакт", "order": 1, "color": "#94A3B8", "description": "Новый лид из бота/сайта"},
            {"name": "Консультация", "order": 2, "color": "#3B82F6", "description": "Запланирована/проведена консультация"},
            {"name": "Принимают решение", "order": 3, "color": "#F59E0B", "description": "Клиент рассматривает предложение"},
            {"name": "Куплена услуга", "order": 4, "color": "#10B981", "description": "Оплата получена, программа выдана"},
            {"name": "Активный клиент", "order": 5, "color": "#8B5CF6", "description": "Клиент выполняет программу"},
            {"name": "Завершен", "order": 6, "color": "#6B7280", "description": "Программа завершена"},
            {"name": "Неактивен", "order": 7, "color": "#EF4444", "description": "Клиент не отвечает/потерян"},
        ]
        
        for stage_data in stages:
            stage = PipelineStage(**stage_data)
            db.add(stage)
        
        db.commit()
        logger.info(f"Created {len(stages)} default pipeline stages")
    except Exception as e:
        logger.error(f"Error creating default pipeline stages: {e}")
        db.rollback()
    finally:
        db.close()


def create_default_admin_user():
    """Create default admin user."""
    db = get_db_session()
    try:
        # Load env (in case script is run directly)
        load_dotenv()

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@fitness.local")

        # Check if admin exists
        admin = db.query(User).filter(User.username == admin_username).first()
        if admin:
            logger.info("Admin user already exists")
            return
        
        # Hash password from env
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=password_hash,
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        logger.info(f"Created default admin user (username: {admin_username})")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
        db.rollback()
    finally:
        db.close()


def init_crm():
    """Initialize CRM system - create tables and default data."""
    logger.info("Initializing CRM system...")
    create_tables()
    create_default_pipeline_stages()
    create_default_admin_user()
    logger.info("CRM system initialized successfully")


if __name__ == "__main__":
    init_crm()

