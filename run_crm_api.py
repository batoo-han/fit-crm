"""Script to run CRM API server."""
import uvicorn
import sys
import logging

# Настраиваем логирование uvicorn, чтобы скрыть ошибки перезагрузки
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

# Подавляем KeyboardInterrupt при перезагрузке
import signal
import sys

def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения."""
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Отключаем стандартное логирование uvicorn, используем loguru
    # Это предотвращает конфликты при перезагрузке
    try:
        uvicorn.run(
            "crm_api.main:app",
            host="127.0.0.1",
            port=8009,
            reload=True,
            reload_dirs=["crm_api", "database"],  # Указываем только нужные директории
            reload_excludes=["*.pyc", "__pycache__", "*.log", "*.py~"],  # Исключаем ненужные файлы
            log_level="warning",  # Уменьшаем уровень логирования uvicorn
            access_log=False,  # Отключаем access log, используем loguru
            use_colors=True,
            reload_includes=["*.py"]  # Отслеживаем только Python файлы
        )
    except KeyboardInterrupt:
        # Игнорируем KeyboardInterrupt при перезагрузке
        pass

