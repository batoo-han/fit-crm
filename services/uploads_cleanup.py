"""Сервис для очистки папки uploads от неиспользуемых файлов и удаления битых ссылок из БД."""
import re
from pathlib import Path
from database.db import get_db_session
from database.models import WebsiteSettings
from database.models_crm import ProgramTemplate, CampaignMessage
from loguru import logger


def cleanup_uploads():
    """
    Очистка папки uploads:
    1. Удаляет файлы, на которые нет ссылок в БД
    2. Удаляет ссылки из БД, если файла больше нет
    """
    db = get_db_session()
    try:
        uploads_dir = Path("uploads")
        if not uploads_dir.exists():
            logger.info("Папка uploads не существует, создаём её")
            uploads_dir.mkdir(exist_ok=True)
            return

        # Получаем все файлы в папке uploads
        files_in_dir = set()
        for file_path in uploads_dir.iterdir():
            if file_path.is_file():
                files_in_dir.add(file_path.name)

        if not files_in_dir:
            logger.info("Папка uploads пуста, очистка не требуется")
            return

        logger.info(f"Найдено {len(files_in_dir)} файлов в папке uploads")

        # Получаем все ссылки на файлы из БД
        # Проверяем WebsiteSettings
        all_settings = db.query(WebsiteSettings).all()
        referenced_files = set()

        def extract_file_references(text: str) -> set:
            """Извлекает все ссылки на файлы из текста."""
            if not text:
                return set()
            
            files = set()
            value_str = str(text)
            
            # Паттерн для поиска ссылок на файлы в uploads
            # Ищем: /uploads/имя_файла или uploads/имя_файла
            patterns = [
                r'/uploads/([^/\s"\'<>]+)',  # /uploads/filename.ext
                r'uploads/([^/\s"\'<>]+)',    # uploads/filename.ext (без слэша)
            ]

            for pattern in patterns:
                matches = re.findall(pattern, value_str, re.IGNORECASE)
                for match in matches:
                    # Убираем возможные параметры запроса и фрагменты URL
                    filename = match.split('?')[0].split('#')[0].strip()
                    if filename:
                        files.add(filename)
            
            return files

        # Проверяем WebsiteSettings
        for setting in all_settings:
            if setting.setting_value:
                referenced_files.update(extract_file_references(setting.setting_value))

        # Проверяем ProgramTemplate (могут быть ссылки в content)
        program_templates = db.query(ProgramTemplate).all()
        for template in program_templates:
            if template.content:
                referenced_files.update(extract_file_references(template.content))

        # Проверяем CampaignMessage (могут быть ссылки в body_text)
        campaign_messages = db.query(CampaignMessage).all()
        for message in campaign_messages:
            if message.body_text:
                referenced_files.update(extract_file_references(message.body_text))

        logger.info(f"Найдено {len(referenced_files)} уникальных файлов, на которые есть ссылки в БД")

        # 1. Удаляем файлы, на которые нет ссылок в БД
        files_to_delete = files_in_dir - referenced_files
        deleted_count = 0
        for filename in files_to_delete:
            try:
                file_path = uploads_dir / filename
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Удалён неиспользуемый файл: {filename}")
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {filename}: {e}")

        if deleted_count > 0:
            logger.info(f"Удалено {deleted_count} неиспользуемых файлов из папки uploads")

        # 2. Удаляем ссылки из БД, если файла больше нет
        broken_references = referenced_files - files_in_dir
        if broken_references:
            logger.info(f"Найдено {len(broken_references)} битых ссылок в БД")
            
            def remove_broken_references(text: str, broken_files: set) -> str:
                """Удаляет битые ссылки из текста."""
                if not text:
                    return text
                
                updated_value = str(text)
                for broken_file in broken_files:
                    # Заменяем различные форматы ссылок на пустую строку
                    patterns_to_remove = [
                        f'/uploads/{broken_file}',
                        f'uploads/{broken_file}',
                        f'"/uploads/{broken_file}"',
                        f'"uploads/{broken_file}"',
                        f"'/uploads/{broken_file}'",
                        f"'uploads/{broken_file}'",
                    ]
                    
                    for pattern in patterns_to_remove:
                        # Удаляем ссылку с возможными пробелами вокруг
                        updated_value = re.sub(
                            rf'\s*{re.escape(pattern)}\s*',
                            '',
                            updated_value,
                            flags=re.IGNORECASE
                        )
                
                return updated_value
            
            updated_count = 0
            
            # Обновляем WebsiteSettings
            for setting in all_settings:
                if not setting.setting_value:
                    continue

                original_value = str(setting.setting_value)
                updated_value = remove_broken_references(original_value, broken_references)

                if updated_value != original_value:
                    # Если после удаления ссылки значение стало пустым или только пробелами, устанавливаем None
                    if not updated_value.strip() or updated_value.strip() == '""' or updated_value.strip() == "''":
                        setting.setting_value = None
                    else:
                        setting.setting_value = updated_value.strip()
                    updated_count += 1
                    logger.debug(f"Обновлена настройка {setting.setting_key}: удалена битая ссылка")

            # Обновляем ProgramTemplate
            for template in program_templates:
                if template.content:
                    original_value = str(template.content)
                    updated_value = remove_broken_references(original_value, broken_references)
                    if updated_value != original_value:
                        template.content = updated_value.strip() if updated_value.strip() else None
                        updated_count += 1
                        logger.debug(f"Обновлён шаблон программы {template.id}: удалена битая ссылка")

            # Обновляем CampaignMessage
            for message in campaign_messages:
                if message.body_text:
                    original_value = str(message.body_text)
                    updated_value = remove_broken_references(original_value, broken_references)
                    if updated_value != original_value:
                        message.body_text = updated_value.strip() if updated_value.strip() else None
                        updated_count += 1
                        logger.debug(f"Обновлено сообщение кампании {message.id}: удалена битая ссылка")

            if updated_count > 0:
                db.commit()
                logger.info(f"Обновлено {updated_count} записей в БД: удалены битые ссылки")
            else:
                db.rollback()

        if deleted_count == 0 and len(broken_references) == 0:
            logger.info("Очистка uploads завершена: все файлы используются, битых ссылок нет")

    except Exception as e:
        logger.error(f"Ошибка при очистке uploads: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
    finally:
        db.close()

