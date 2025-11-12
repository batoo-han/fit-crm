#!/usr/bin/env python3
"""Скрипт для миграции: добавление колонки pipeline_id в таблицу client_pipelines."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import engine, get_db_session
from sqlalchemy import text, inspect
from loguru import logger

def migrate_client_pipelines():
    """Добавить колонку pipeline_id в client_pipelines если её нет."""
    try:
        inspector = inspect(engine)
        
        # Проверяем, существует ли таблица
        if "client_pipelines" not in inspector.get_table_names():
            logger.warning("Таблица client_pipelines не существует, миграция не требуется")
            return False
        
        # Проверяем, существует ли колонка
        columns = [col["name"] for col in inspector.get_columns("client_pipelines")]
        if "pipeline_id" in columns:
            logger.info("Колонка pipeline_id уже существует в client_pipelines")
            return True
        
        # Добавляем колонку
        logger.info("Добавляем колонку pipeline_id в client_pipelines...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE client_pipelines ADD COLUMN pipeline_id INTEGER"))
            conn.commit()
        
        logger.info("Колонка pipeline_id успешно добавлена в client_pipelines")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при миграции client_pipelines: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_client_pipelines()
    sys.exit(0 if success else 1)

