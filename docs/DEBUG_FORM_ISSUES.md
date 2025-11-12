# Диагностика проблем с формой обратной связи

## Что было исправлено

1. **Улучшена обработка ошибок в `dnk/script.js`**:
   - Добавлена проверка парсинга JSON ответа
   - Более детальное логирование ошибок в консоль
   - Обработка различных форматов ошибок от API

2. **Улучшена обработка ошибок в API (`crm_api/routers/website.py`)**:
   - Добавлено детальное логирование с traceback
   - Разделение HTTP исключений и общих исключений
   - Более информативные сообщения об ошибках

## Как диагностировать проблему

### 1. Проверьте логи API контейнера

```bash
docker logs crm_api_prod --tail 100 --follow
```

Затем отправьте форму и посмотрите, какая ошибка появляется в логах.

### 2. Проверьте доступность API

```bash
# Проверка health-check
curl https://www.batoohan.ru/api/health

# Проверка эндпоинта формы (должен вернуть 405 Method Not Allowed для GET)
curl -X GET https://www.batoohan.ru/api/website/contact

# Тестовая отправка формы
curl -X POST https://www.batoohan.ru/api/website/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "+79001234567",
    "service": "online_1_month",
    "message": "Test message"
  }'
```

### 3. Проверьте консоль браузера

Откройте DevTools (F12) → вкладка Console и Network:
- В Console должны появиться детальные логи ошибок
- В Network посмотрите на запрос к `/api/website/contact`:
  - Статус код
  - Response body (что вернул сервер)

### 4. Типичные проблемы и решения

#### Проблема: "502 Bad Gateway"
**Причина**: API контейнер не запущен или упал
**Решение**: 
```bash
docker ps | grep crm_api_prod
docker logs crm_api_prod --tail 50
docker-compose -f docker-compose.production.yml restart api
```

#### Проблема: "500 Internal Server Error" с деталями в логах
**Причина**: Ошибка в коде API (отсутствие таблицы, неправильный импорт и т.д.)
**Решение**: 
1. Проверьте логи API
2. Убедитесь, что база данных инициализирована:
   ```bash
   docker exec -it crm_api_prod python -c "from database.init_crm import init_crm; init_crm()"
   ```

#### Проблема: "Ошибка парсинга ответа"
**Причина**: API возвращает не JSON (например, HTML страницу ошибки)
**Решение**: 
- Проверьте, что nginx правильно проксирует запросы
- Проверьте конфигурацию nginx: `sudo nginx -t`

#### Проблема: Ошибка при создании клиента/контакта
**Причина**: Проблемы с базой данных (отсутствие таблиц, неправильные связи)
**Решение**: 
1. Проверьте структуру БД:
   ```bash
   docker exec -it crm_api_prod python -c "from database.db import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
   ```
2. Переинициализируйте БД (осторожно - удалит данные):
   ```bash
   docker exec -it crm_api_prod python database/init_crm.py
   ```

### 5. Проверка зависимостей

Убедитесь, что все необходимые сервисы доступны:

```bash
# Проверка Telegram бота (для отправки уведомлений)
docker logs crm_bot_prod --tail 20

# Проверка переменных окружения
docker exec -it crm_api_prod env | grep -E "TELEGRAM|ADMIN|DATABASE"
```

## После исправления

После применения исправлений:

1. **Обновите файлы на сервере**:
   ```bash
   # Скопируйте обновленный script.js в /var/www/dnk/
   # Скопируйте обновленный код API
   ```

2. **Пересоберите и перезапустите контейнеры**:
   ```bash
   docker-compose -f docker-compose.production.yml build api
   docker-compose -f docker-compose.production.yml up -d api
   ```

3. **Проверьте работу**:
   - Откройте сайт
   - Откройте консоль браузера (F12)
   - Отправьте тестовую форму
   - Проверьте логи API

## Контакты для отладки

Если проблема не решается, соберите следующую информацию:

1. Вывод `docker logs crm_api_prod --tail 200`
2. Скриншот консоли браузера (Console и Network)
3. Вывод `curl -X POST https://www.batoohan.ru/api/website/contact ...` (см. выше)
4. Статус контейнеров: `docker ps`

