"""Migration script to add CRM fields to clients table."""
import sys
from pathlib import Path
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL

# Simple logger
def log_info(msg):
    print(f"INFO: {msg}")

def log_error(msg):
    print(f"ERROR: {msg}")

def migrate_add_crm_fields():
    """Add CRM fields to clients table."""
    try:
        # Extract database path from DATABASE_URL
        if DATABASE_URL.startswith("sqlite:///"):
            db_path = DATABASE_URL.replace("sqlite:///", "")
        else:
            log_error("Only SQLite databases are supported for this migration")
            return False
        
        log_info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(clients)")
        columns = [row[1] for row in cursor.fetchall()]
        log_info(f"Existing columns: {columns}")
        
        # Add pipeline_stage_id if it doesn't exist
        if 'pipeline_stage_id' not in columns:
            log_info("Adding pipeline_stage_id column...")
            cursor.execute("""
                ALTER TABLE clients 
                ADD COLUMN pipeline_stage_id INTEGER
            """)
            conn.commit()
            log_info("✓ Added pipeline_stage_id column")
        else:
            log_info("pipeline_stage_id column already exists")
        
        # Add last_contact_at if it doesn't exist
        if 'last_contact_at' not in columns:
            log_info("Adding last_contact_at column...")
            cursor.execute("""
                ALTER TABLE clients 
                ADD COLUMN last_contact_at DATETIME
            """)
            conn.commit()
            log_info("✓ Added last_contact_at column")
        else:
            log_info("last_contact_at column already exists")
        
        # Add next_contact_at if it doesn't exist
        if 'next_contact_at' not in columns:
            log_info("Adding next_contact_at column...")
            cursor.execute("""
                ALTER TABLE clients 
                ADD COLUMN next_contact_at DATETIME
            """)
            conn.commit()
            log_info("✓ Added next_contact_at column")
        else:
            log_info("next_contact_at column already exists")
        
        # Add created_at if it doesn't exist
        if 'created_at' not in columns:
            log_info("Adding created_at column...")
            cursor.execute("""
                ALTER TABLE clients 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            conn.commit()
            log_info("✓ Added created_at column")
        else:
            log_info("created_at column already exists")
        
        # Add updated_at if it doesn't exist
        if 'updated_at' not in columns:
            log_info("Adding updated_at column...")
            cursor.execute("""
                ALTER TABLE clients 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            conn.commit()
            log_info("✓ Added updated_at column")
        else:
            log_info("updated_at column already exists")
        
        # Migrate training_programs table
        log_info("Checking training_programs table...")
        cursor.execute("PRAGMA table_info(training_programs)")
        program_columns = [row[1] for row in cursor.fetchall()]
        log_info(f"Existing training_programs columns: {program_columns}")
        
        # Add formatted_program if it doesn't exist
        if 'formatted_program' not in program_columns:
            log_info("Adding formatted_program column...")
            cursor.execute("""
                ALTER TABLE training_programs 
                ADD COLUMN formatted_program TEXT
            """)
            conn.commit()
            log_info("✓ Added formatted_program column")
        else:
            log_info("formatted_program column already exists")
        
        # Add is_paid if it doesn't exist
        if 'is_paid' not in program_columns:
            log_info("Adding is_paid column...")
            cursor.execute("""
                ALTER TABLE training_programs 
                ADD COLUMN is_paid BOOLEAN DEFAULT 0
            """)
            conn.commit()
            log_info("✓ Added is_paid column")
        else:
            log_info("is_paid column already exists")
        
        # Add assigned_by if it doesn't exist
        if 'assigned_by' not in program_columns:
            log_info("Adding assigned_by column...")
            cursor.execute("""
                ALTER TABLE training_programs 
                ADD COLUMN assigned_by INTEGER
            """)
            conn.commit()
            log_info("✓ Added assigned_by column")
        else:
            log_info("assigned_by column already exists")
        
        # Add assigned_at if it doesn't exist
        if 'assigned_at' not in program_columns:
            log_info("Adding assigned_at column...")
            cursor.execute("""
                ALTER TABLE training_programs 
                ADD COLUMN assigned_at DATETIME
            """)
            conn.commit()
            log_info("✓ Added assigned_at column")
        else:
            log_info("assigned_at column already exists")
        
        conn.close()
        log_info("✅ Migration completed successfully!")
        print("✅ Миграция завершена успешно!")
        return True
        
    except Exception as e:
        log_error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"❌ Ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    migrate_add_crm_fields()

