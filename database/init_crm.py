"""Initialize CRM models and create default data."""
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db_session, engine
from database.models import Base
from database.models_crm import (
    PipelineStage, User, ClientPipeline, ClientAction,
    ClientContact, ProgressJournal, ClientBotLink, Reminder, FAQ, SalesScenario
)
from sqlalchemy import inspect, text
from loguru import logger
import bcrypt
import os
from dotenv import load_dotenv


def create_tables():
    """Create all database tables."""
    try:
        # Import all models to register them with Base.metadata
        # This ensures all tables are created
        from database.models import Client, TrainingProgram, Payment, Lead, WebsiteContact, WebsiteSettings, ProgramVersion
        from database.models_crm import (
            PipelineStage, User, ClientPipeline, ClientAction,
            ClientContact, ProgressJournal, ClientBotLink, Reminder, FAQ, SalesScenario, SalesPipeline,
            MarketingCampaign, CampaignAudience, CampaignMessage, CampaignRun, ClientChannelPreference, CampaignDelivery,
            SocialPost, PromoCode, PromoUsage, SocialPostTemplate
        )
        
        # Create all tables first
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Then ensure optional columns (for migrations)
        ensure_optional_columns()
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        raise


def ensure_optional_columns():
    """Ensure newly added columns exist when upgrading in-place."""
    try:
        inspector = inspect(engine)

        def table_exists(table: str) -> bool:
            """Check if table exists."""
            try:
                return table in inspector.get_table_names()
            except Exception:
                return False

        def ensure(table: str, column: str, ddl: str):
            """Ensure column exists in table."""
            if not table_exists(table):
                logger.debug(f"Table {table} does not exist, skipping column check")
                return
            columns = [col["name"] for col in inspector.get_columns(table)]
            if column not in columns:
                logger.info(f"Adding missing column {table}.{column}")
                with engine.connect() as conn:
                    # DDL should include column name and type, e.g., "email VARCHAR(255)"
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                    conn.commit()

        ensure("clients", "email", "VARCHAR(255)")
        
        # Migrate metadata to payment_metadata if needed
        if table_exists("payments"):
            try:
                columns = [col["name"] for col in inspector.get_columns("payments")]
                if "metadata" in columns and "payment_metadata" not in columns:
                    logger.info("Migrating payments.metadata to payments.payment_metadata")
                    with engine.connect() as conn:
                        # Try RENAME COLUMN (SQLite 3.25+)
                        try:
                            conn.execute(text("ALTER TABLE payments RENAME COLUMN metadata TO payment_metadata"))
                            conn.commit()
                            logger.info("Successfully migrated metadata column to payment_metadata using RENAME COLUMN")
                        except Exception as rename_error:
                            # Fallback: create new column, copy data
                            logger.warning(f"RENAME COLUMN not supported, using copy method: {rename_error}")
                            # Create new column
                            conn.execute(text("ALTER TABLE payments ADD COLUMN payment_metadata TEXT"))
                            # Copy data
                            conn.execute(text("UPDATE payments SET payment_metadata = metadata WHERE metadata IS NOT NULL"))
                            conn.commit()
                            logger.info("Successfully migrated metadata column to payment_metadata using copy method")
                            # Note: Old 'metadata' column will remain but can be ignored
                elif "payment_metadata" not in columns:
                    ensure("payments", "payment_metadata", "TEXT")
            except Exception as e:
                logger.warning(f"Could not migrate metadata column: {e}")
        
        # Ensure pipeline_id column exists in pipeline_stages (for multi-pipeline support)
        ensure("pipeline_stages", "pipeline_id", "INTEGER")
            
    except Exception as e:
        logger.error(f"Error ensuring optional columns: {e}")


def create_default_pipeline_stages():
    """Create default pipeline stages."""
    db = get_db_session()
    try:
        # Check if stages already exist using direct SQL to avoid column issues
        try:
            result = db.execute(text("SELECT COUNT(*) FROM pipeline_stages"))
            existing = result.scalar()
            if existing > 0:
                logger.info("Pipeline stages already exist, skipping creation")
                return
        except Exception as count_error:
            logger.warning(f"Could not check existing stages: {count_error}, proceeding with creation")
        
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
    
    # Initialize default FAQ and sales scenarios
    try:
        from database.init_faq_data import create_default_faq
        create_default_faq()
    except Exception as e:
        logger.error(f"Error creating default FAQ: {e}")
    
    try:
        from database.init_sales_scenarios import create_default_sales_scenarios
        create_default_sales_scenarios()
    except Exception as e:
        logger.error(f"Error creating default sales scenarios: {e}")
    
    logger.info("CRM system initialized successfully")


if __name__ == "__main__":
    init_crm()

