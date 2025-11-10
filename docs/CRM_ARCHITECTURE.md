# Архитектура CRM системы для фитнес-тренера

## Обзор

CRM система для управления клиентами, тренировочными программами, воронками продаж и отслеживания прогресса клиентов.

## Технологический стек

### Backend
- **FastAPI** - современный, быстрый веб-фреймворк для создания API
- **SQLAlchemy** - ORM для работы с БД
- **Alembic** - миграции БД
- **Pydantic** - валидация данных
- **JWT** - аутентификация

### Frontend
- **React 18** - UI библиотека
- **TypeScript** - типизация
- **Vite** - сборщик
- **React Router** - маршрутизация
- **TanStack Query (React Query)** - управление состоянием и кэширование
- **Tailwind CSS** - стилизация
- **Recharts** - графики и аналитика
- **React Hook Form** - формы

### База данных
- **SQLite** (текущая) / **PostgreSQL** (для продакшена)

## Структура базы данных

### Новые таблицы

#### 1. PipelineStage (Воронка продаж)
```python
- id: Integer (PK)
- name: String (название этапа)
- order: Integer (порядок в воронке)
- color: String (цвет для UI)
- created_at: DateTime
```

#### 2. ClientPipeline (Связь клиента с воронкой)
```python
- id: Integer (PK)
- client_id: Integer (FK -> clients.id)
- stage_id: Integer (FK -> pipeline_stages.id)
- moved_at: DateTime
- moved_by: Integer (FK -> users.id, опционально)
- notes: Text
```

#### 3. ClientAction (Действия с клиентом)
```python
- id: Integer (PK)
- client_id: Integer (FK -> clients.id)
- action_type: String (call, message, meeting, email, etc.)
- action_date: DateTime
- description: Text
- created_by: Integer (FK -> users.id)
- created_at: DateTime
```

#### 4. ClientContact (Контакты с клиентом)
```python
- id: Integer (PK)
- client_id: Integer (FK -> clients.id)
- contact_type: String (telegram, whatsapp, email, phone)
- contact_data: String (номер телефона, username, email)
- message_text: Text
- direction: String (inbound, outbound)
- created_at: DateTime
```

#### 5. ProgressJournal (Дневник параметров)
```python
- id: Integer (PK)
- client_id: Integer (FK -> clients.id)
- program_id: Integer (FK -> training_programs.id)
- measurement_date: DateTime
- period: String (before, week_1, week_2, week_3, week_4, etc.)
- weight: Float
- chest: Float
- waist: Float
- lower_abdomen: Float
- glutes: Float
- right_thigh: Float
- left_thigh: Float
- right_calf: Float
- left_calf: Float
- right_arm: Float
- left_arm: Float
- notes: Text
- created_at: DateTime
```

#### 6. User (Пользователи CRM - тренеры/админы)
```python
- id: Integer (PK)
- username: String (unique)
- email: String (unique)
- password_hash: String
- role: String (admin, trainer)
- is_active: Boolean
- created_at: DateTime
```

### Расширение существующих таблиц

#### TrainingProgram
```python
- Добавить: formatted_program: Text (отформатированный текст программы)
- Добавить: is_paid: Boolean (оплачена ли программа)
- Добавить: assigned_by: Integer (FK -> users.id)
- Добавить: assigned_at: DateTime
```

#### Client
```python
- Добавить: pipeline_stage_id: Integer (FK -> pipeline_stages.id)
- Добавить: last_contact_at: DateTime
- Добавить: next_contact_at: DateTime
```

## API Endpoints

### Аутентификация
- `POST /api/auth/login` - вход
- `POST /api/auth/logout` - выход
- `GET /api/auth/me` - текущий пользователь

### Клиенты
- `GET /api/clients` - список клиентов (с фильтрами и пагинацией)
- `GET /api/clients/{id}` - детали клиента
- `PUT /api/clients/{id}` - обновление клиента
- `GET /api/clients/{id}/programs` - программы клиента
- `GET /api/clients/{id}/payments` - платежи клиента
- `GET /api/clients/{id}/progress` - прогресс клиента
- `GET /api/clients/{id}/actions` - действия с клиентом
- `GET /api/clients/{id}/contacts` - контакты с клиентом

### Воронки
- `GET /api/pipeline/stages` - все этапы воронки
- `POST /api/pipeline/stages` - создать этап
- `PUT /api/pipeline/stages/{id}` - обновить этап
- `POST /api/clients/{id}/move-stage` - переместить клиента по воронке
- `GET /api/pipeline/analytics` - аналитика по воронке

### Программы тренировок
- `GET /api/programs` - список программ
- `GET /api/programs/{id}` - детали программы
- `PUT /api/programs/{id}` - обновить программу
- `POST /api/programs/{id}/assign` - назначить программу клиенту
- `GET /api/programs/{id}/view` - просмотр программы (таблица)

### Дневник параметров
- `GET /api/progress/{client_id}` - все записи прогресса клиента
- `POST /api/progress` - создать запись прогресса
- `PUT /api/progress/{id}` - обновить запись
- `GET /api/progress/{client_id}/chart` - график прогресса

### Действия
- `POST /api/actions` - создать действие
- `GET /api/actions` - список действий (с фильтрами)

### Контакты
- `POST /api/contacts` - создать контакт
- `GET /api/contacts` - список контактов (с фильтрами)

### Аналитика
- `GET /api/analytics/overview` - общая статистика
- `GET /api/analytics/conversion` - конверсия по воронке
- `GET /api/analytics/revenue` - доходы
- `GET /api/analytics/clients-growth` - рост клиентов

## Структура фронтенда

```
crm-frontend/
├── src/
│   ├── components/
│   │   ├── common/          # Общие компоненты
│   │   ├── clients/         # Компоненты клиентов
│   │   ├── pipeline/        # Компоненты воронки
│   │   ├── programs/        # Компоненты программ
│   │   ├── progress/        # Компоненты дневника
│   │   └── analytics/       # Компоненты аналитики
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Clients.tsx
│   │   ├── ClientDetail.tsx
│   │   ├── Pipeline.tsx
│   │   ├── Programs.tsx
│   │   ├── ProgramView.tsx
│   │   ├── Progress.tsx
│   │   └── Analytics.tsx
│   ├── api/                 # API клиент
│   ├── hooks/               # Custom hooks
│   ├── store/               # State management
│   ├── types/               # TypeScript типы
│   └── utils/               # Утилиты
```

## Воронка продаж

### Этапы (Pipeline Stages)
1. **Первичный контакт** - новый лид из бота/сайта
2. **Консультация** - запланирована/проведена консультация
3. **Принимают решение** - клиент рассматривает предложение
4. **Куплена услуга** - оплата получена, программа выдана
5. **Активный клиент** - клиент выполняет программу
6. **Завершен** - программа завершена
7. **Неактивен** - клиент не отвечает/потерян

## Интеграция с Telegram ботом

1. При создании клиента в боте - автоматически создается запись в CRM
2. При оплате - автоматически перемещение в воронку "Куплена услуга"
3. При выдаче программы - автоматическое создание записи в CRM
4. Webhook от бота в CRM API для синхронизации данных

## План реализации

### Этап 1: База данных и модели
- [x] Создать новые модели БД
- [ ] Создать миграции Alembic
- [ ] Обновить существующие модели

### Этап 2: Backend API
- [ ] Настроить FastAPI проект
- [ ] Реализовать аутентификацию
- [ ] Реализовать CRUD для клиентов
- [ ] Реализовать управление воронками
- [ ] Реализовать управление программами
- [ ] Реализовать дневник параметров
- [ ] Реализовать аналитику

### Этап 3: Интеграция с ботом
- [ ] Webhook для синхронизации данных
- [ ] Автоматическое создание записей при оплате
- [ ] Автоматическое назначение программ

### Этап 4: Frontend
- [ ] Настроить React проект
- [ ] Создать базовую структуру
- [ ] Реализовать Dashboard
- [ ] Реализовать страницу клиентов
- [ ] Реализовать воронку продаж
- [ ] Реализовать просмотр программ
- [ ] Реализовать дневник параметров
- [ ] Реализовать аналитику

### Этап 5: Тестирование и доработка
- [ ] Тестирование API
- [ ] Тестирование фронтенда
- [ ] Интеграционное тестирование
- [ ] Оптимизация производительности

