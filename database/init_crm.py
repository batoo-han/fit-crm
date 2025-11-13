"""Initialize CRM models and create default data."""
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db_session, engine
from database.models import Base
from database.models_crm import (
    PipelineStage, User, ClientPipeline, ClientAction,
    ClientContact, ProgressJournal, ClientBotLink, Reminder, FAQ, SalesScenario, ProgramTemplate
)
from sqlalchemy import inspect, text, or_
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
            ProgramTemplate, ProgramHistory,
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
        logger.info("Starting ensure_optional_columns()...")
        inspector = inspect(engine)
        logger.info("Inspector created successfully")

        def table_exists(table: str) -> bool:
            """Check if table exists."""
            try:
                logger.debug(f"Checking if table {table} exists...")
                tables = inspector.get_table_names()
                logger.debug(f"Found {len(tables)} tables")
                return table in tables
            except Exception as e:
                logger.warning(f"Error checking table {table}: {e}")
                return False

        def ensure(table: str, column: str, ddl: str):
            """Ensure column exists in table."""
            if not table_exists(table):
                logger.debug(f"Table {table} does not exist, skipping column check")
                return
            try:
                columns = [col["name"] for col in inspector.get_columns(table)]
            except Exception as e:
                logger.warning(f"Could not get columns for {table}: {e}, trying direct SQL")
                # Fallback: use direct SQL query
                with engine.connect() as conn:
                    result = conn.execute(text(f"PRAGMA table_info({table})"))
                    columns = [row[1] for row in result]
            
            if column not in columns:
                logger.info(f"Adding missing column {table}.{column}")
                try:
                    with engine.connect() as conn:
                        # DDL should include column name and type, e.g., "email VARCHAR(255)"
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                        conn.commit()
                    logger.info(f"Successfully added column {table}.{column}")
                except Exception as e:
                    logger.error(f"Failed to add column {table}.{column}: {e}")
                    raise

        logger.info("Ensuring clients.email column...")
        ensure("clients", "email", "VARCHAR(255)")
        logger.info("clients.email check completed")
        
        # Ensure payments table has promo_code and related columns
        if table_exists("payments"):
            logger.info("Ensuring payments table columns...")
            ensure("payments", "promo_code", "VARCHAR(100)")
            ensure("payments", "discount_amount", "FLOAT")
            ensure("payments", "final_amount", "FLOAT")
            logger.info("payments table columns check completed")
        
        # Migrate metadata to payment_metadata if needed
        logger.info("Checking payments table for metadata migration...")
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
        logger.info("Ensuring pipeline_stages.pipeline_id column...")
        ensure("pipeline_stages", "pipeline_id", "INTEGER")
        logger.info("pipeline_stages.pipeline_id check completed")
        
        # Ensure pipeline_id column exists in client_pipelines (for multi-pipeline support)
        logger.info("Ensuring client_pipelines.pipeline_id column...")
        ensure("client_pipelines", "pipeline_id", "INTEGER")
        logger.info("client_pipelines.pipeline_id check completed")
        
        # Ensure training_programs.sent_at column
        if table_exists("training_programs"):
            logger.info("Ensuring training_programs.sent_at column...")
            ensure("training_programs", "sent_at", "DATETIME")
            logger.info("training_programs.sent_at check completed")
        
        logger.info("ensure_optional_columns() completed successfully")
            
    except Exception as e:
        logger.error(f"Error ensuring optional columns: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


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

        # Check if admin exists by username or email
        admin = db.query(User).filter(
            or_(User.username == admin_username, User.email == admin_email)
        ).first()

        # Hash password from env
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if admin:
            updates = []
            if admin.username != admin_username:
                admin.username = admin_username
                updates.append("username")
            if admin.email != admin_email:
                admin.email = admin_email
                updates.append("email")
            admin.password_hash = password_hash
            admin.role = "admin"
            admin.is_active = True
            db.commit()
            logger.info(
                "Updated existing admin user ({}), changed: {}".format(
                    admin.username,
                    ", ".join(updates) if updates else "password"
                )
            )
        else:
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


def create_default_program_templates():
    """Create default program templates if they don't exist."""
    try:
        db = get_db_session()
        try:
            # Check if default footer template exists
            footer_template = db.query(ProgramTemplate).filter(
                ProgramTemplate.template_type == "footer",
                ProgramTemplate.is_default == True
            ).first()
            
            if not footer_template:
                default_footer = ProgramTemplate(
                    name="Разъяснения по использованию программы (по умолчанию)",
                    template_type="footer",
                    content="""ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ ПРОГРАММЫ ТРЕНИРОВОК

1. ОРГАНИЗАЦИЯ ТРЕНИРОВОЧНОГО ПРОЦЕССА

• Следуйте программе строго по порядку недель и дней
• Записывайте максимальный рабочий вес в колонку "Вес*" после каждой тренировки
• Отдых между подходами: 60-90 секунд для новичков, 90-120 секунд для продвинутых
• Между тренировками должен быть минимум 1 день отдыха

2. ТЕХНИКА ВЫПОЛНЕНИЯ

• Приоритет - правильная техника, а не вес
• Если упражнение вызывает боль - используйте альтернативу
• Контролируйте каждое движение, избегайте рывков
• Полная амплитуда движения обязательна

3. ПРОГРЕССИЯ

• Увеличивайте вес только когда можете выполнить все подходы с правильной техникой
• Если указан диапазон повторений (например, 12-16), начинайте с меньшего числа
• Когда достигнете верхнего предела - увеличивайте вес на 2.5-5 кг

4. РАЗГРУЗОЧНЫЕ НЕДЕЛИ

• Каждая 4-я неделя - разгрузочная (объём снижен на 20%)
• Это необходимо для восстановления и предотвращения перетренированности
• Не пропускайте разгрузочные недели

5. ПИТАНИЕ И ВОССТАНОВЛЕНИЕ

• Пейте достаточно воды (30-40 мл на 1 кг веса)
• Спите не менее 7-8 часов
• Питайтесь сбалансированно, учитывая ваши цели

6. ВОПРОСЫ И ПОДДЕРЖКА

• При возникновении вопросов обращайтесь к тренеру
• Тренер: {trainer_name}
• Телефон: {trainer_phone}
• Telegram: {trainer_telegram}

Удачи в тренировках! 💪""",
                    description="Стандартный шаблон разъяснений для PDF программ",
                    is_active=True,
                    is_default=True
                )
                db.add(default_footer)
                db.commit()
                logger.info("Created default footer template")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating default program templates: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


def init_crm():
    """Initialize CRM system - create tables and default data."""
    logger.info("Initializing CRM system...")
    try:
        logger.info("Step 1: Creating tables...")
        create_tables()
        logger.info("Step 1 completed: Tables created")
    except Exception as e:
        logger.error(f"Error in create_tables: {e}")
        raise
    
    try:
        logger.info("Step 2: Creating default pipeline stages...")
        create_default_pipeline_stages()
        logger.info("Step 2 completed: Pipeline stages created")
    except Exception as e:
        logger.error(f"Error in create_default_pipeline_stages: {e}")
        # Не критично, продолжаем
    
    try:
        logger.info("Step 3: Creating default admin user...")
        create_default_admin_user()
        logger.info("Step 3 completed: Admin user created/updated")
    except Exception as e:
        logger.error(f"Error in create_default_admin_user: {e}")
        # Не критично, продолжаем
    
    # Initialize default FAQ and sales scenarios
    try:
        logger.info("Step 4: Creating default FAQ...")
        from database.init_faq_data import create_default_faq
        create_default_faq()
        logger.info("Step 4 completed: FAQ created")
    except Exception as e:
        logger.error(f"Error creating default FAQ: {e}")
        # Не критично, продолжаем
    
    try:
        logger.info("Step 5: Creating default sales scenarios...")
        from database.init_sales_scenarios import create_default_sales_scenarios
        create_default_sales_scenarios()
        logger.info("Step 5 completed: Sales scenarios created")
    except Exception as e:
        logger.error(f"Error creating default sales scenarios: {e}")
        # Не критично, продолжаем
    
    # Step 6: Create default program templates
    create_default_program_templates()
    
    logger.info("CRM system initialized successfully")


if __name__ == "__main__":
    init_crm()

