# Исправление миграции таблицы client_pipelines

## Проблема

При отправке формы обратной связи возникает ошибка:
```
sqlite3.OperationalError: table client_pipelines has no column named pipeline_id
```

## Причина

В модели `ClientPipeline` есть поле `pipeline_id`, но в существующей базе данных эта колонка отсутствует. Это происходит, если база была создана до добавления этого поля.

## Решение

Добавлена автоматическая миграция в `database/init_crm.py`, которая проверяет наличие колонки `pipeline_id` в таблице `client_pipelines` и добавляет её, если она отсутствует.

## Как применить на сервере

### Вариант 1: Автоматическая миграция (рекомендуется)

1. **Обновите код на сервере** (скопируйте обновленный `database/init_crm.py`)

2. **Перезапустите API контейнер**:
   ```bash
   docker-compose -f docker-compose.production.yml restart api
   ```
   
   При старте API автоматически вызовет `init_crm()`, который выполнит миграцию.

3. **Проверьте логи**:
   ```bash
   docker logs crm_api_prod --tail 50
   ```
   
   Должна появиться строка:
   ```
   Adding missing column client_pipelines.pipeline_id
   ```

### Вариант 2: Ручная миграция (если автоматическая не сработала)

Если по какой-то причине автоматическая миграция не сработала, можно выполнить миграцию вручную:

```bash
# Подключитесь к контейнеру
docker exec -it crm_api_prod python

# В Python выполните:
from database.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Проверяем, существует ли колонка
    result = conn.execute(text("PRAGMA table_info(client_pipelines)"))
    columns = [row[1] for row in result]
    
    if 'pipeline_id' not in columns:
        print("Добавляем колонку pipeline_id...")
        conn.execute(text("ALTER TABLE client_pipelines ADD COLUMN pipeline_id INTEGER"))
        conn.commit()
        print("Колонка добавлена успешно!")
    else:
        print("Колонка pipeline_id уже существует")
```

Или напрямую через SQLite:

```bash
# Найдите путь к базе данных
docker exec -it crm_api_prod ls -la /data/

# Выполните миграцию (замените путь к БД на актуальный)
docker exec -it crm_api_prod sqlite3 /data/crm.db "ALTER TABLE client_pipelines ADD COLUMN pipeline_id INTEGER;"
```

## Проверка

После применения миграции:

1. **Проверьте структуру таблицы**:
   ```bash
   docker exec -it crm_api_prod python -c "
   from database.db import engine
   from sqlalchemy import inspect, text
   inspector = inspect(engine)
   columns = [col['name'] for col in inspector.get_columns('client_pipelines')]
   print('Колонки в client_pipelines:', columns)
   print('pipeline_id присутствует:', 'pipeline_id' in columns)
   "
   ```

2. **Попробуйте отправить форму** с сайта - ошибка должна исчезнуть.

3. **Проверьте логи API** при отправке формы:
   ```bash
   docker logs crm_api_prod --tail 20 --follow
   ```

## Дополнительная информация

Колонка `pipeline_id` используется для поддержки множественных воронок продаж. Если воронка не указана, значение будет `NULL`, что соответствует "дефолтной" воронке.

После миграции все существующие записи в `client_pipelines` будут иметь `pipeline_id = NULL`, что является корректным значением для дефолтной воронки.

