# Диагностика зависания при старте API

## Проблема

API контейнер зависает при старте, логи показывают только:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started parent process [1]
```

И дальше ничего не происходит.

## Что было исправлено

1. **Добавлено детальное логирование** в `init_crm()` и `ensure_optional_columns()`:
   - Каждый шаг инициализации теперь логируется
   - Можно точно определить, где процесс зависает

2. **Улучшена обработка ошибок**:
   - API продолжит запуск даже при ошибках инициализации (кроме критических)
   - Все ошибки логируются с полным traceback

## Диагностика

### Шаг 1: Обновите код и пересоберите контейнер

```bash
# Обновите файлы на сервере:
# - crm_api/main.py
# - database/init_crm.py

# Пересоберите и перезапустите
docker-compose -f docker-compose.production.yml build api
docker-compose -f docker-compose.production.yml up -d api
```

### Шаг 2: Следите за логами в реальном времени

```bash
docker logs crm_api_prod --follow
```

Теперь вы должны увидеть детальные логи:
```
Starting CRM API...
Calling init_crm()...
Initializing CRM system...
Step 1: Creating tables...
Starting ensure_optional_columns()...
...
```

**Определите, на каком шаге зависает процесс.**

### Шаг 3: Возможные причины зависания

#### Причина 1: Блокировка базы данных

Если процесс зависает на операциях с БД, возможно, база заблокирована другим процессом.

**Решение:**
```bash
# Проверьте, нет ли других процессов, использующих БД
docker exec -it crm_api_prod ls -la /data/crm.db*

# Если нужно, остановите все контейнеры и перезапустите
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

#### Причина 2: Проблема с inspector.get_table_names()

Если зависает на `inspector.get_table_names()`, возможно, проблема с подключением к БД.

**Решение:**
```bash
# Проверьте доступность файла БД
docker exec -it crm_api_prod ls -la /data/crm.db

# Проверьте права доступа
docker exec -it crm_api_prod stat /data/crm.db
```

#### Причина 3: Проблема с миграцией колонки

Если зависает на добавлении колонки `pipeline_id`, возможно, таблица заблокирована.

**Решение:**
Выполните миграцию вручную (см. `docs/FIX_CLIENT_PIPELINES_MIGRATION.md`)

### Шаг 4: Временное решение - пропустить инициализацию

Если нужно срочно запустить API, можно временно закомментировать `init_crm()` в `crm_api/main.py`:

```python
# Временно отключено для диагностики
# init_crm()
```

Но это не рекомендуется, так как таблицы могут не существовать.

## Альтернативный подход: Запуск миграции отдельно

Если инициализация блокирует запуск, можно выполнить миграцию отдельно:

```bash
# Выполните миграцию вручную
docker exec -it crm_api_prod python -c "
from database.db import engine
from sqlalchemy import text, inspect

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('client_pipelines')]

if 'pipeline_id' not in columns:
    print('Добавляем колонку pipeline_id...')
    with engine.connect() as conn:
        conn.execute(text('ALTER TABLE client_pipelines ADD COLUMN pipeline_id INTEGER'))
        conn.commit()
    print('Колонка добавлена успешно!')
else:
    print('Колонка pipeline_id уже существует')
"
```

Затем перезапустите API без инициализации (или с пропуском миграций).

## Проверка после исправления

После применения исправлений:

1. **Проверьте логи** - должны появиться детальные сообщения о каждом шаге
2. **Определите точку зависания** - на каком шаге останавливается процесс
3. **Пришлите логи** - с детальными логами можно точно определить проблему

## Если проблема сохраняется

Соберите следующую информацию:

1. Полные логи API:
   ```bash
   docker logs crm_api_prod > api_logs.txt
   ```

2. Статус контейнера:
   ```bash
   docker ps -a | grep crm_api_prod
   docker inspect crm_api_prod | grep -A 10 State
   ```

3. Информация о БД:
   ```bash
   docker exec -it crm_api_prod ls -la /data/
   docker exec -it crm_api_prod stat /data/crm.db
   ```

4. Попытка подключения к БД:
   ```bash
   docker exec -it crm_api_prod python -c "from database.db import engine; print(engine.connect())"
   ```

