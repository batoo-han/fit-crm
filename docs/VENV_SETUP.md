# Настройка виртуального окружения .venv

## Создание виртуального окружения

```bash
# Windows PowerShell
python -m venv .venv

# Linux/Mac
python3 -m venv .venv
```

## Активация окружения

### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows CMD
```cmd
.venv\Scripts\activate.bat
```

### Linux/Mac
```bash
source .venv/bin/activate
```

После активации в начале строки терминала появится префикс `(.venv)`.

## Установка зависимостей

```bash
# После активации окружения
pip install -r requirements.txt
```

## Деактивация окружения

```bash
deactivate
```

## Проверка установки

```bash
# Проверить версию Python в окружении
python --version

# Проверить установленные пакеты
pip list

# Проверить конкретный пакет
pip show aiogram
```

## Обновление requirements.txt

Если установили новый пакет, обновите `requirements.txt`:

```bash
pip freeze > requirements.txt
```

## Полезные команды

```bash
# Установить конкретную версию пакета
pip install aiogram==3.3.0

# Обновить все пакеты
pip install --upgrade -r requirements.txt

# Удалить пакет
pip uninstall package_name

# Создать requirements.txt без версий
pip freeze | grep -v "^-e" > requirements.txt
```

## Структура проекта

```
workflow/
├── .venv/              # Виртуальное окружение (не в Git)
├── .env                # Переменные окружения (не в Git)
├── bot.py              # Главный файл
├── requirements.txt    # Зависимости
└── ...
```

## Важно

- Не коммитьте `.venv/` в Git
- Не коммитьте `.env` в Git
- Всегда используйте `.venv` для разработки
- Обновляйте `requirements.txt` при добавлении новых зависимостей
