"""Database migration script to add new questionnaire fields."""
from database.db import engine, Base
from database.models import Client
from sqlalchemy import inspect
from loguru import logger

def migrate_database():
    """Add new columns to Client table if they don't exist."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('clients')]
    
    new_columns = {
        'height': 'INTEGER',
        'weight': 'REAL',
        'bmi': 'REAL',
        'health_restrictions': 'TEXT',
        'lifestyle': 'VARCHAR(50)',
        'training_history': 'TEXT',
        'equipment': 'TEXT',
        'nutrition': 'TEXT'
    }
    
    with engine.connect() as conn:
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                try:
                    conn.execute(f"ALTER TABLE clients ADD COLUMN {column_name} {column_type}")
                    logger.info(f"Added column {column_name} to clients table")
                except Exception as e:
                    logger.error(f"Error adding column {column_name}: {e}")
        
        conn.commit()
        logger.info("Database migration completed")

if __name__ == "__main__":
    migrate_database()
