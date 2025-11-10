"""Script to reset admin password."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_db_session
from database.models_crm import User
from loguru import logger
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def reset_admin_password():
    """Reset admin password from .env file."""
    db = get_db_session()
    try:
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        admin = db.query(User).filter(User.username == admin_username).first()
        if not admin:
            logger.error(f"Admin user '{admin_username}' not found!")
            print(f"❌ Пользователь '{admin_username}' не найден в базе данных.")
            print("Запустите: python database/init_crm.py")
            return False
        
        # Hash new password
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password
        admin.password_hash = password_hash
        db.commit()
        
        logger.info(f"Password reset for user: {admin_username}")
        print(f"✅ Пароль для пользователя '{admin_username}' успешно обновлен!")
        print(f"   Используйте пароль из .env файла: {admin_password}")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        db.rollback()
        print(f"❌ Ошибка при сбросе пароля: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()

