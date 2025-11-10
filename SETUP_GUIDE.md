# Руководство по установке и эксплуатации

> Этот документ описывает полный цикл развёртывания и обслуживания платформы: API, админ-панели, Telegram-бота и вспомогательных сервисов. Для краткого обзора см. `README.md`.

## Содержание
1. [Общая архитектура](#общая-архитектура)
2. [Предварительные требования](#предварительные-требования)
3. [Переменные окружения](#переменные-окружения)
4. [Подготовка окружения для разработки](#подготовка-окружения-для-разработки)
5. [Инициализация базы данных](#инициализация-базы-данных)
6. [Запуск сервисов локально](#запуск-сервисов-локально)
7. [Настройка YooKassa для локальной разработки](#настройка-yookassa-для-локальной-разработки)
8. [Деплой через Docker (Ubuntu Server)](#деплой-через-docker-ubuntu-server)
9. [Обслуживание и обновления](#обслуживание-и-обновления)
10. [Резервное копирование и восстановление](#резервное-копирование-и-восстановление)
11. [Устранение неполадок](#устранение-неполадок)
12. [Полезные советы](#полезные-советы)

## Общая архитектура

```
┌────────────┐   HTTP (REST)   ┌────────────┐
│  Frontend  │◄──────────────►│   FastAPI   │◄────────────┐
│ (React/TW) │                │  (crm_api)  │             │
└─────┬──────┘                └──────┬──────┘             │
      │                              │                    │
      │ WebSockets/HTTP              │ ORM                │
      ▼                              ▼                    ▼
┌────────────┐                ┌────────────┐       ┌────────────┐
│ Website UI │                │   SQLite    │◄────►│  Services  │
│ (dnk/*)    │                │  database   │      │ (LLM, etc) │
└────────────┘                └────────────┘       └────────────┘
      │
      ▼
┌────────────┐
│ Telegram   │
│  Bot       │
└────────────┘
```

- **FastAPI (`crm_api/`)** — центральный API, обрабатывает CRM-логику, сайт, чат-виджет, уведомления.
- **React-панель (`crm-frontend/`)** — админ-интерфейс для сотрудников (управление клиентами, настройками, аналитикой).
- **Сайт (`dnk/`)** — статический фронт (не версионируется, используется как шаблон, выкатка вручную).
- **Telegram-бот (`bot.py`)** — пользовательский touchpoint.
- **Services (`services/`)** — вспомогательные модули: генерация программ, интеграция LLM, телеграм-уведомления и т.д.

## Предварительные требования

- Git, Python 3.11+, Node.js 20+ (для локальной разработки фронтенда).
- Docker и Docker Compose (для контейнерного деплоя).
- Telegram Bot Token и ID администратора.
- Ключи LLM-провайдеров (YandexGPT, OpenAI/ProxyAPI) при использовании виджета.
- Сервер на Ubuntu 20.04+ (для продакшн размещения).

## Переменные окружения

Используется файл `.env`. Скопируйте `.env.example` и заполните актуальными значениями.

```bash
cp .env.example .env
nano .env
```

Основные группы переменных:

- **База данных и общие настройки**
  - `DATABASE_URL` — строка подключения; по умолчанию `sqlite:///data/crm.db`.
  - `LOG_LEVEL`, `LOG_FILE` — журналирование.
- **Telegram**
  - `TELEGRAM_BOT_TOKEN`
  - `ADMIN_CHAT_ID` — для уведомлений и контакт-формы сайта.
- **LLM**
  - `LLM_PROVIDER` (значения: `yandex`, `openai`, `proxyapi`)
  - Ключи: `YANDEX_GPT_API_KEY`, `OPENAI_API_KEY`, `PROXYAPI_API_KEY`.
- **Почта / интеграции (при необходимости)**
  - Email SMTP, платежные системы и т.п. — добавляются по мере реализации.

> Не храните `.env` в Git. Все секреты остаются на сервере.

## Подготовка окружения для разработки

### 1. Python backend
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Node.js frontend
```bash
cd crm-frontend
npm install
```

### 3. Проверка зависимостей
```bash
python -m pip check
npm run lint   # при наличии линтера
```

## Инициализация базы данных

- **Первый запуск (SQLite)**
  ```bash
  python database/init_crm.py
  ```
  Скрипт создаёт все таблицы и директорию `data/` при необходимости.

- **Миграции**
  Используется декларативная генерация через SQLAlchemy; при изменении моделей пересоздайте таблицы или подготовьте скрипты миграции вручную (Alembic по желанию).

## Запуск сервисов локально

### FastAPI (CRM API)
```bash
python run_crm_api.py
```
Параметры:
- `reload` активирован, отслеживает изменения в `crm_api/` и `database/`.
- Логи в `logs/api.log` (создаётся автоматически).
- CORS позволяет работать с `localhost` и `file://` (тестирование сайта).

### React admin panel
```bash
cd crm-frontend
npm run dev  # порт 5173
```
Настройте `crm-frontend/src/services/api.ts`, чтобы dev-сервер обращался к API (по умолчанию `http://localhost:8009/api`).

### Telegram-бот
```bash
python bot.py
```
Логи бота — в `logs/bot.log`. Убедитесь, что `TELEGRAM_BOT_TOKEN` и `ADMIN_CHAT_ID` заполнены.

### Единый запуск всех сервисов

Чтобы одновременно поднять CRM API (FastAPI), React dev server и Telegram-бота, воспользуйтесь скриптом `run_all.py`:

```bash
python run_all.py
```

Скрипт запускает три подпроцесса, следит за их состоянием и корректно завершает их при `Ctrl+C`. Перед запуском убедитесь, что:

- установлены Python-зависимости (`pip install -r requirements.txt`);
- выполнен `npm install` в каталоге `crm-frontend`.

### Статический сайт

Папка `dnk/` исключена из Git. Для локального тестирования:
```bash
cd dnk
python -m http.server 8009  # либо откройте index.html вручную (учтите CORS)
```
Настройте `script.js` для корректного обращения к API (локально: `http://localhost:8009/api/...`). Для продакшна обновите URL на актуальный домен.

## Деплой через Docker (Ubuntu Server)

### Установка Docker и Compose
```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER  # перелогиньтесь
```

### Подготовка проекта
```bash
# Копирование исходников (git clone / scp / rsync)
git clone <repo_url> /opt/fitness-crm
cd /opt/fitness-crm

# Конфигурация окружения
cp .env.example .env
nano .env  # заполните значения
```

### Запуск контейнеров
```bash
docker compose up -d --build
docker compose ps
```

- `crm_frontend` слушает порт 80 (Nginx + React build).
- `crm_api` — внутренний сервис (порт 8000).
- SQLite файлы сохраняются в volume `crm_data` (`/data/crm.db` внутри контейнера).

### Проверка
- Откройте `http://<сервер>/` — должна загрузиться админ-панель.
- Запрос к `http://<сервер>/api/health` (если настроена точка здоровья) или выполните `docker compose logs api`.

### HTTPS
Используйте внешний reverse-proxy (Caddy, Traefik, Nginx) или Cloudflare. Проксируйте на порт 80 контейнера `crm_frontend`.

## Обслуживание и обновления

### Обновление приложения
```bash
git pull
docker compose up -d --build
```

### Просмотр логов
```bash
docker compose logs -f api      # логи API
docker compose logs -f frontend # логи Nginx/React
```

### Перезапуск сервисов
```bash
docker compose restart api
docker compose restart frontend
```

### Остановка
```bash
docker compose down
# docker compose down -v   # с удалением volumes (аккуратно!)
```

## Резервное копирование и восстановление

### База данных (SQLite)
```bash
CONTAINER_ID=$(docker compose ps -q api)
docker cp ${CONTAINER_ID}:/data/crm.db ./backup_crm_$(date +%F).db
```

Для восстановления скопируйте файл обратно в `/data/crm.db` контейнера или volume, затем перезапустите сервис.

### Логи
Volume `crm_logs` содержит файлы журналов. Копируйте по аналогии с БД или используйте `docker cp`.

## Настройка YooKassa для локальной разработки

### Шаг 1: Регистрация и получение тестовых ключей

1. **Зарегистрируйтесь в YooKassa**:
   - Перейдите на https://yookassa.ru/
   - Зарегистрируйте личный кабинет или войдите, если уже есть аккаунт

2. **Создайте магазин (тестовый)**:
   - В личном кабинете перейдите в раздел "Магазины"
   - Создайте новый магазин (для тестирования можно указать любые данные)
   - После создания магазина вы получите:
     - **Shop ID** (идентификатор магазина)
     - **Секретный ключ** (Secret Key)

3. **Получите тестовые ключи**:
   - В настройках магазина найдите раздел "API"
   - Скопируйте **Shop ID** и **Секретный ключ**
   - Для тестирования можно использовать тестовый режим (режим "Песочница")

### Шаг 2: Настройка переменных окружения

Добавьте полученные ключи в файл `.env`:

```bash
# YooKassa Configuration
YOOKASSA_SHOP_ID=your_shop_id_here
YOOKASSA_SECRET_KEY=your_secret_key_here
YOOKASSA_RETURN_URL=https://www.batoohan.ru/pay/return
```

**Важно**: Для локальной разработки `YOOKASSA_RETURN_URL` можно оставить как есть или изменить на `http://localhost:8009/pay/return` (это URL, на который пользователь вернется после оплаты).

### Шаг 3: Установка и настройка ngrok

Для локальной разработки необходимо настроить туннель, чтобы YooKassa мог отправлять webhook на ваш локальный сервер.

#### Установка ngrok

**Windows**:
1. Скачайте ngrok с https://ngrok.com/download
2. Распакуйте архив
3. Добавьте `ngrok.exe` в PATH или используйте полный путь

**Linux/macOS**:
```bash
# Через Homebrew (macOS)
brew install ngrok

# Или скачайте бинарник с https://ngrok.com/download
# И добавьте в PATH
```

#### Регистрация в ngrok (опционально, но рекомендуется)

1. Зарегистрируйтесь на https://ngrok.com/ (бесплатно)
2. Получите авторизационный токен
3. Авторизуйтесь:
   ```bash
   ngrok config add-authtoken ваш_токен
   ```

#### Запуск ngrok

1. **Убедитесь, что API запущен на порту 8009**:
   ```bash
   python run_crm_api.py
   # или
   python -m uvicorn crm_api.main:app --host 0.0.0.0 --port 8009
   ```

2. **В отдельном терминале запустите ngrok**:
   ```bash
   ngrok http 8009
   ```

3. **Скопируйте HTTPS URL** из вывода ngrok:
   ```
   Forwarding  https://abc123-def456.ngrok-free.app -> http://localhost:8009
   ```
   В данном примере URL: `https://abc123-def456.ngrok-free.app`

**Примечание**: Бесплатный ngrok генерирует новый URL при каждом запуске. Для постоянного URL можно:
- Использовать платный план ngrok
- Или каждый раз обновлять webhook в YooKassa при перезапуске ngrok

### Шаг 4: Настройка webhook в YooKassa

1. **Войдите в личный кабинет YooKassa**:
   - Перейдите на https://yookassa.ru/my
   - Войдите в свой аккаунт

2. **Перейдите в настройки магазина**:
   - Выберите ваш магазин
   - Перейдите в раздел "Настройки" → "Уведомления" (или "Webhooks")

3. **Добавьте URL webhook**:
   - URL должен быть: `https://ваш-ngrok-url.ngrok-free.app/api/payments/webhook/yookassa`
   - Например: `https://abc123-def456.ngrok-free.app/api/payments/webhook/yookassa`
   - **Важно**: Используйте HTTPS URL от ngrok, не HTTP!

4. **Выберите события**:
   - Отметьте `payment.succeeded` (платеж успешно завершен)
   - Отметьте `payment.canceled` (платеж отменен)
   - Можно также отметить `payment.waiting_for_capture` (ожидает подтверждения)

5. **Сохраните настройки**

### Шаг 5: Тестирование платежей

#### Тестовые карты YooKassa

YooKassa предоставляет тестовые карты для проверки платежей:

**Успешный платеж**:
- Номер карты: `5555 5555 5555 4444`
- Срок действия: любая будущая дата (например, `12/25`)
- CVV: любой трехзначный код (например, `123`)
- Имя держателя: любое имя

**Отклоненный платеж**:
- Номер карты: `5555 5555 5555 4477`
- Остальные данные: любые

**Карта, требующая 3-D Secure**:
- Номер карты: `5555 5555 5555 4444`
- При оплате потребуется ввести код из SMS

#### Проверка работы

1. **Запустите все сервисы**:
   ```bash
   # Терминал 1: API
   python run_crm_api.py
   
   # Терминал 2: ngrok
   ngrok http 8009
   
   # Терминал 3: Бот
   python bot.py
   ```

2. **Создайте тестовый платеж**:
   - Откройте Telegram бота
   - Выполните команду `/price`
   - Выберите любую услугу
   - Нажмите на кнопку оплаты
   - Введите тестовые данные карты

3. **Проверьте логи**:
   ```bash
   # Логи API (должен быть запрос на webhook)
   tail -f logs/api.log | grep webhook
   
   # Логи бота (должна быть проверка платежей)
   tail -f logs/bot.log | grep payment
   ```

4. **Проверьте статус в CRM**:
   - Откройте админ-панель
   - Перейдите в раздел "Клиенты"
   - Найдите клиента, который создал платеж
   - Проверьте, что платеж имеет статус `completed`
   - Проверьте, что клиент переместился в этап "Куплена услуга"

### Шаг 6: Проверка webhook вручную

Вы можете проверить, что webhook работает, отправив тестовый запрос:

```bash
# Замените URL на ваш ngrok URL
curl -X POST https://abc123-def456.ngrok-free.app/api/payments/webhook/yookassa \
  -H "Content-Type: application/json" \
  -d '{
    "type": "notification",
    "event": "payment.succeeded",
    "object": {
      "id": "test_payment_id",
      "status": "succeeded",
      "amount": {
        "value": "1000.00",
        "currency": "RUB"
      },
      "metadata": {
        "payment_id": "1"
      }
    }
  }'
```

### Устранение проблем

**Проблема: webhook не приходит**
- Убедитесь, что ngrok запущен и URL актуален
- Проверьте, что URL в настройках YooKassa правильный (с `/api/payments/webhook/yookassa`)
- Убедитесь, что API запущен на порту 8009
- Проверьте логи ngrok: должны быть входящие запросы

**Проблема: "Invalid webhook URL"**
- Убедитесь, что используется HTTPS URL (не HTTP)
- Проверьте, что URL доступен из интернета (проверьте через браузер)
- Убедитесь, что в URL нет лишних символов

**Проблема: платеж создается, но статус не обновляется**
- Проверьте логи API на наличие ошибок
- Убедитесь, что `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` правильные
- Проверьте, что webhook настроен в YooKassa
- Бот проверяет платежи каждые 5 минут, подождите или проверьте вручную через API

**Проблема: ngrok URL меняется при каждом запуске**
- Зарегистрируйтесь в ngrok и настройте резервирование домена (платная функция)
- Или используйте сервис типа `localhost.run` (бесплатный статический URL)
- Или обновляйте webhook в YooKassa каждый раз при перезапуске ngrok

### Альтернативные решения для локальной разработки

1. **localhost.run** (бесплатный статический URL):
   ```bash
   ssh -R 80:localhost:8009 serveo.net
   # Получите URL вида: https://abc123.serveo.net
   ```

2. **serveo.net** (бесплатный SSH туннель):
   ```bash
   ssh -R 80:localhost:8009 serveo.net
   ```

3. **Локальная разработка без webhook**:
   - Можно не настраивать webhook для локальной разработки
   - Бот будет проверять платежи каждые 5 минут
   - Это достаточно для тестирования, но обновление будет не мгновенным

### Переход на production

Когда будете готовы к production:

1. **Получите production ключи** в YooKassa
2. **Обновите `.env`** с production ключами
3. **Настройте webhook** на production URL: `https://ваш-домен.ru/api/payments/webhook/yookassa`
4. **Убедитесь, что SSL сертификат настроен** (HTTPS обязателен для webhook)
5. **Протестируйте** с реальными платежами на небольшие суммы

**Примечание**: Бот также периодически проверяет статус платежей каждые 5 минут, поэтому webhook не является обязательным, но значительно ускоряет обновление статуса.

## Устранение неполадок

| Симптом | Возможная причина | Решение |
|---------|-------------------|---------|
| `ModuleNotFoundError: email_validator` | Зависимость не установлена | `pip install -r requirements.txt` (в контейнере или локально) |
| `sqlite3.OperationalError` | Нет прав на запись в volume | Проверьте права на хосте, убедитесь что volume создан |
| CORS ошибки при открытии `index.html` локально | `file://` origin | Запускайте локальный web-сервер или убедитесь, что `crm_api` разрешает `null` origin (уже настроено) |
| `sqlalchemy.exc.NoReferencedTableError` | Не импортированы модели при создании БД | Убедитесь, что `database/db.py` импортирует все модели перед `Base.metadata.create_all()` (исправлено) |
| Нет ответа Telegram-бота | Неверный токен или бот не запущен | Проверьте `.env`, логи `bot.log`, перезапустите бота |
| Виджет чата показывает неправильную модель LLM | Конфигурация не синхронизирована | Обновите настройки в панели (`Настройки сайта → Виджет чата`), сохраните |

## Полезные советы

- `dnk/` находится вне Git — храните актуальный билд сайта отдельно, деплойте вручную.
- При изменении моделей в `database/models.py` убедитесь, что связанные сервисы обновлены (например, удаление клиентов учитывает все внешние ключи).
- Настройки сайта (`/website-settings`) позволяют обновлять промпт, цвета, контент без правок кода.
- Для разработки LLM-логики используйте тестовые ключи и ограничьте токены через настройки виджета.

---

Для вопросов по бизнес-логике см. `docs/ADMIN_GUIDE.md`. Для взаимодействия с интерфейсами клиентов см. `docs/USER_GUIDE.md`.

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