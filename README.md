# Автоматизированная система продаж фитнес-тренировок

## Описание проекта

Система для автоматизации продаж персональных фитнес-тренировок тренера Данилы Цыганкова (D&K FitBody).

## Архитектура

### MVP - Telegram бот "Фитнес-ассистент"
- Бесплатная раздача программ тренировок
- Опросник для квалификации клиентов
- Сбор контактов и перенаправление на оплату
- Базовая CRM через Google Sheets

### Технологический стек
- Python 3.9+
- aiogram (Telegram Bot Framework)
- SQLite/PostgreSQL для базы данных
- Google Sheets API для временного хранения
- YandexGPT/OpenAI API для AI-агента

## Установка

```bash
# Клонировать репозиторий
git clone <repo_url>

# Перейти в директорию
cd workflow

# Создать виртуальное окружение
python -m venv .venv

# Активировать окружение
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env файл

# Запустить бота
python bot.py
```

## Структура проекта

```
workflow/
├── bot.py                 # Основной файл Telegram-бота
├── handlers/              # Обработчики команд
├── database/              # Модели базы данных
├── services/              # Бизнес-логика
├── config/                # Конфигурация
├── data/                  # Данные (планы тренировок)
├── templates/             # Шаблоны сообщений
└── requirements.txt       # Зависимости Python
```

## Конфигурация

Создайте файл `.env` со следующими переменными:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=sqlite:///bot.db
GOOGLE_SHEETS_CREDENTIALS=path/to/credentials.json
YANDEX_API_KEY=your_yandex_api_key
OPENAI_API_KEY=your_openai_key  # Опционально
AMOCRM_DOMAIN=your_domain
AMOCRM_CLIENT_ID=your_client_id
AMOCRM_CLIENT_SECRET=your_client_secret
```

## Запуск

```bash
python bot.py
```

## Разработка

### Добавление новых функций
1. Создайте handler в `handlers/`
2. Добавьте роут в `bot.py`
3. Обновите базу данных при необходимости
4. Добавьте тесты

## Лицензия

Проприетарное программное обеспечение. Все права защищены.

## Контакты

Тренер: Данила Цыганков
Telegram: @DandK_FitBody
WhatsApp: +7 (909) 920 2195
