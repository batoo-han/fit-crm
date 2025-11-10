# Руководство по установке и запуску

## Быстрый старт

### 1. Предварительные требования

- Python 3.9 или выше
- Telegram аккаунт
- Telegram Bot Token (получить у @BotFather)

### 2. Установка

```bash
# Клонировать репозиторий (если он в git)
# git clone <repo_url>
# cd workflow

# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
copy .env.example .env
# Или в Linux/Mac:
# cp .env.example .env
```

### 3. Настройка бота

Отредактируйте файл `.env` и добавьте необходимые данные:

```env
# ОБЯЗАТЕЛЬНЫЕ НАСТРОЙКИ

# Telegram Bot Token (получить у @BotFather в Telegram)
TELEGRAM_BOT_TOKEN=ваш_токен_бота

# ID администратора (ваш Telegram ID)
ADMIN_CHAT_ID=ваш_chat_id
```

Чтобы получить свой Chat ID:
1. Напишите @userinfobot в Telegram
2. Бот вернет ваш ID
3. Скопируйте ID в ADMIN_CHAT_ID

### 4. Инициализация базы данных

```bash
python setup.py
```

Эта команда создаст:
- Базу данных (SQLite)
- Необходимые директории
- Проверит настройки

### 5. Запуск бота

```bash
python bot.py
```

Если все настроено правильно, вы увидите:
```
✅ Bot started successfully!
```

## Расширенные настройки

### Интеграция с Google Sheets

**Вариант 1: Публичные таблицы (рекомендуется)**

Не требует credentials.json! Просто убедитесь, что таблицы доступны для чтения:

1. Откройте Google Sheets таблицу
2. Нажмите "Настроить доступ"
3. Выберите "Все, у кого есть ссылка" → "Читатель"
4. Добавьте ссылки в `.env` (уже есть в примере)

**Вариант 2: С credentials.json (для приватных таблиц)**

Если таблицы приватные:

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com)
2. Включите Google Sheets API
3. Создайте Service Account
4. Скачайте credentials.json
5. Положите файл в корень проекта
6. Добавьте в .env:
```env
GOOGLE_SHEETS_CREDENTIALS=credentials.json
```

Система автоматически выберет способ доступа к таблицам.

### Интеграция с amoCRM (этап 2)

Для интеграции с CRM:

```env
AMOCRM_DOMAIN=ваш_домен.amocrm.ru
AMOCRM_CLIENT_ID=ваш_client_id
AMOCRM_CLIENT_SECRET=ваш_secret
```

### Интеграция с платежными системами (этап 2)

Для приема платежей через Tinkoff:

```env
TINKOFF_TERMINAL_KEY=ваш_terminal_key
TINKOFF_PASSWORD=ваш_password
```

## Проверка работы

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Проверьте работу всех кнопок

## Команды для администратора

- `/stats` - показать статистику бота (только для админа)
- `/start` - главное меню
- `/program` - получить программу
- `/price` - узнать цены
- `/contacts` - контакты тренера
- `/faq` - часто задаваемые вопросы

## Структура проекта

```
workflow/
├── bot.py                 # Основной файл бота
├── config.py              # Конфигурация
├── setup.py               # Скрипт установки
├── requirements.txt       # Зависимости Python
├── .env                   # Переменные окружения (создать!)
├── handlers/              # Обработчики команд
│   ├── start.py          # Команда /start
│   ├── questionnaire.py  # Опросник
│   ├── payment.py        # Платежи
│   ├── contacts.py       # Контакты
│   ├── faq.py           # FAQ
│   └── admin.py         # Админ-команды
├── database/             # База данных
│   ├── models.py        # Модели данных
│   └── db.py           # Инициализация БД
├── services/            # Сервисы (будущие)
├── data/                # Данные
└── logs/                # Логи
```

## Устранение неполадок

### Ошибка: "TELEGRAM_BOT_TOKEN is required"

Убедитесь, что вы:
1. Создали файл `.env`
2. Добавили токен бота
3. Правильно указали путь к файлу

### Ошибка: "Module not found"

Установите зависимости:
```bash
pip install -r requirements.txt
```

### Бот не отвечает

1. Проверьте, что бот запущен
2. Проверьте логи в `logs/bot.log`
3. Убедитесь, что токен правильный

### Проблемы с базой данных

Удалите базу и создайте заново:
```bash
rm bot.db
python setup.py
```

## Дальнейшие шаги

После успешного запуска MVP:

1. ✅ Протестировать бота на первых клиентах
2. ✅ Настроить Google Sheets для хранения данных
3. ✅ Добавить интеграцию с amoCRM
4. ✅ Настроить платежную систему
5. ✅ Добавить AI-агента для ответов на вопросы
6. ✅ Реализовать автоматическую генерацию программ

## Поддержка

При возникновении проблем:
- Проверьте логи в `logs/bot.log`
- Обратитесь к тренеру: @DandK_FitBody
- Создайте issue в репозитории (если проект в Git)

## Деплой через Docker (Ubuntu Server)

### Предварительные требования
- Ubuntu 20.04+ с правами sudo
- Установлены Docker и Docker Compose:
  ```bash
  sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker $USER
  # Перелогиньтесь после добавления в группу
  ```

### Подготовка окружения
1. Скопируйте проект на сервер (git clone или rsync/scp).
2. Создайте `.env` из примера и заполните переменные (в т.ч. `ADMIN_CHAT_ID`, API ключи LLM при необходимости):
   ```bash
   cp .env.example .env
   nano .env
   ```
3. Проверьте, что каталог `dnk/` не попадает в репозиторий (он игнорируется и предназначен только для локальных правок сайта).

### Запуск
```bash
# Собрать и запустить в фоне
docker compose up -d --build

# Проверить статус контейнеров
docker compose ps

# Просмотреть логи API
docker compose logs -f api
```

### Сеть и доступ
- Фронтенд доступен по HTTP на порту 80 сервера.
- Все запросы к `/api/*` проксируются во внутренний сервис API.
- База данных SQLite хранится в volume `crm_data` по пути контейнера `/data` (персистентно).

### Обновление версии
```bash
git pull
docker compose pull || true
docker compose up -d --build
```

### Резервное копирование
```bash
# Экспорт SQLite файла из volume
CONTAINER_ID=$(docker compose ps -q api)
docker cp ${CONTAINER_ID}:/data/crm.db ./backup_crm_$(date +%F).db
```

### Откат/остановка
```bash
docker compose down
# Для полного удаления volumes (данные будут удалены!)
# docker compose down -v
```

### Примечания
- Переменная `DATABASE_URL` уже сконфигурирована для SQLite в контейнере (`sqlite:////data/crm.db`).
- Логи пишутся в volume `crm_logs`.
- Если нужен HTTPS, поставьте обратный прокси (Caddy/Traefik/Nginx) перед фронтендом с сертификатами и проксируйте на порт 80 контейнера фронтенда.