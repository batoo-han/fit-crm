# Автоматизированная система продаж фитнес-тренировок (CRM + LLM)

Комплексная платформа для фитнес-бизнеса тренера Данилы Цыганкова (D&K FitBody). Система объединяет CRM, Telegram-бота, веб-сайт с LLM-ассистентом и административную панель для управления программами, клиентами и маркетингом.

## Ключевые возможности

- **CRM и аналитика**: база клиентов, воронка продаж, платежи, тренинговые программы, журнал прогресса.
- **Генератор программ тренировок**: платные программы и демо-версии (первую неделю).
- **Сайт с контактной формой и LLM-чатом**: обращения сохраняются в CRM, уведомления в Telegram, чат-бот на Yandex GPT/OpenAI.
- **Админ-панель (React)**: настройка сайта, виджета чата, контента, визуальных тем, управление клиентами и программами.
- **Telegram-бот**: выдача программ, FAQ, коммуникация с клиентами.
- **Интеграции**: уведомления в Telegram, гибкое подключение LLM-провайдеров, настройка CORS для локального и продакшн окружений.

## Компоненты проекта

| Компонент | Назначение | Технологии |
|----------|------------|------------|
| `crm_api/` | REST API, бизнес-логика CRM, веб-сервис | FastAPI, SQLAlchemy, Loguru |
| `database/` | Определения моделей и инициализация БД | SQLAlchemy, SQLite (по умолчанию) |
| `services/` | Доменные сервисы (программы, LLM, уведомления) | Python |
| `crm-frontend/` | Веб-интерфейс администратора | React, TypeScript, React Router, React Query, Tailwind CSS |
| `dnk/` | Статический сайт (не входит в репозиторий) | HTML/CSS/JS (локальное тестирование) |
| `bot.py` | Telegram-бот | aiogram |
| `Dockerfile.api`, `crm-frontend/Dockerfile`, `docker-compose.yml` | Контейнеризация | Docker, Nginx |

## Технологический стек

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic, Uvicorn, Loguru.
- **Frontend (CRM)**: React 18, TypeScript, React Query, Tailwind CSS, Vite.
- **AI**: Yandex GPT, OpenAI (через ProxyAPI), настраиваемый системный промпт.
- **Инфраструктура**: Docker, docker-compose, Nginx (reverse proxy), SQLite (по умолчанию) / возможность подключения PostgreSQL.
- **Интеграции**: Telegram (Aiogram), веб-формы, контакт-виджет сайта.

## Документация

- `SETUP_GUIDE.md` — развёртывание и техническая настройка (локально и на Ubuntu Server, Docker).
- `docs/USER_GUIDE.md` — руководство пользователя (клиент, сайт, бот).
- `docs/ADMIN_GUIDE.md` — инструкция администратора (CRM, настройки, LLM, воронка).

## Быстрый старт (Docker)

```bash
# Клонируйте проект и перейдите в папку
git clone <repo_url>
cd workflow

# Создайте .env на основе примера
cp .env.example .env
nano .env   # заполните обязательные переменные

# Соберите и запустите сервисы
docker compose up -d --build

# Проверка
docker compose ps
```

- Панель администратора доступна по `http://<host>/` (порт 80).
- API доступен по `http://<host>/api/...` (proxied через фронтенд).
- Для обновления: `git pull && docker compose up -d --build`.

Подробности — в `SETUP_GUIDE.md`.

### Быстрый старт для разработки (без Docker)

```bash
# 1. Настройте Python-окружение
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Установите зависимости фронтенда
cd crm-frontend && npm install && cd ..

# 3. Запустите всё одной командой
python run_all.py
```

- Админ-панель: http://localhost:5173/
- API: http://localhost:8009/api/
- Telegram-бот запускается внутри общего процесса; завершить все сервисы — `Ctrl+C`.

Если нужно запускать части по отдельности — в разделе «Запуск в режиме разработки» описаны команды для каждого сервиса.

## Запуск в режиме разработки

### Backend (FastAPI)
1. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Настройте `.env` (копия из `.env.example`).
3. Инициализируйте БД (при необходимости) и запустите API:
   ```bash
   python run_crm_api.py
   ```

### Frontend (React)
```bash
cd crm-frontend
npm install
npm run dev  # Vite dev server (порт 5173 по умолчанию)
```

### Telegram-бот
```bash
python bot.py
```

## Структура репозитория (основные директории)

```
workflow/
├── crm_api/               # Бэкенд: роутеры, схемы, middleware
├── crm-frontend/          # Интерфейс администратора (React + Tailwind)
├── database/              # SQLAlchemy модели и инициализация
├── services/              # Бизнес-логика (программы, LLM, уведомления)
├── docs/                  # Руководства для пользователей и администраторов
├── scripts/               # Утилиты и вспомогательные скрипты (при наличии)
├── Dockerfile.api         # Dockerfile для FastAPI сервиса
├── docker-compose.yml     # Оркестрация фронтенда и API
├── SETUP_GUIDE.md         # Пошаговый гайд по установке и деплою
├── README.md              # Этот файл
└── ...
```

> Папка `dnk/` используется только как локальный прототип сайта и исключена из Git. При необходимости обновите код сайта локально и перенесите на сервер вручную.

## Контакты и поддержка

- Тренер: Данила Цыганков (@DandK_FitBody)
- Для технических вопросов — создайте issue в репозитории или свяжитесь по контактам в CRM.

## Лицензия

Проприетарное ПО. Распространение ограничено владельцем проекта.
