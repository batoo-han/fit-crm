# Исправление проблем развертывания

## Проблемы, которые были исправлены

### 1. Циклический редирект в frontend контейнере
**Проблема**: Ошибка `rewrite or internal redirection cycle while internally redirecting to "/admin/index.html"`

**Причина**: В `crm-frontend/nginx.conf` использовался `try_files $uri $uri/ /admin/index.html;`, что создавало цикл редиректов.

**Решение**: Изменена конфигурация на использование `root` вместо `alias` и упрощена логика `try_files`:
```nginx
location /admin/ {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}
```

### 2. API запросы возвращают 404
**Проблема**: Запросы к `/api/website/chat` и `/api/website/purchase` возвращают 404.

**Причина**: API контейнер не пробрасывал порт наружу, поэтому nginx на хосте не мог подключиться к `127.0.0.1:8001`.

**Решение**: В `docker-compose.production.yml` добавлен проброс порта:
```yaml
ports:
  - "127.0.0.1:8001:8000"
```

### 3. Неправильная корневая директория для статического сайта
**Проблема**: В nginx конфигурации была указана неправильная директория.

**Решение**: Исправлена корневая директория в `nginx/nginx.production.conf`:
```nginx
root /var/www/dnk;
```

Дополнительно указаны реальные файлы сертификатов сервера:
```nginx
ssl_certificate /etc/ssl/batoohan.ru.crt;
ssl_certificate_key /etc/ssl/batoohan.ru.key;
```

### 4. Отсутствие health-check для nginx
**Проблема**: `https://www.batoohan.ru/api/health` возвращал 404, хотя nginx проксирует `/api/`.

**Решение**: Добавлен эндпоинт `GET /api/health` в `crm_api/main.py`.

### 5. Telegram-бот и фоновая авторассылка не запускались
**Проблема**: Docker Compose не запускал `bot.py`, из-за чего бот и регулярные задачи (рассылки, проверки платежей) были недоступны.

**Решение**: В `docker-compose.production.yml` добавлен сервис `bot`, использующий тот же образ, но команду `python bot.py`.

## Инструкция по применению исправлений

### На сервере выполните следующие шаги:

1. **Остановите контейнеры**:
```bash
cd /path/to/workflow
docker-compose -f docker-compose.production.yml down
```

2. **Обновите файлы конфигурации**:
   - Скопируйте обновленный `docker-compose.production.yml` на сервер
   - Скопируйте обновленный `nginx/nginx.production.conf` на сервер
   - Скопируйте обновленный `crm-frontend/nginx.conf` на сервер (он будет использован при пересборке)

3. **Обновите конфигурацию nginx на хосте**:
```bash
sudo cp nginx/nginx.production.conf /etc/nginx/sites-available/batoohan.ru
sudo nginx -t  # Проверка конфигурации
sudo systemctl reload nginx
```

4. **Пересоберите и запустите контейнеры**:
```bash
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

5. **Проверьте логи**:
```bash
# Логи frontend контейнера
docker logs crm_frontend_prod

# Логи API контейнера
docker logs crm_api_prod

# Логи nginx на хосте
sudo tail -f /var/log/nginx/batoohan.ru.error.log

# Логи Telegram-бота
docker logs crm_bot_prod
```

6. **Проверьте доступность**:
   - Сайт: `https://batoohan.ru`
   - Админ-панель: `https://batoohan.ru/admin/`
   - API: `https://batoohan.ru/api/website/contact` (должен вернуть 405 Method Not Allowed для GET, но не 404)

## Проверка работоспособности

### Проверка API:
```bash
curl -X POST https://www.batoohan.ru/api/website/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com"}'
```

### Проверка health-check:
```bash
curl https://www.batoohan.ru/api/health
```

### Проверка админ-панели:
Откройте в браузере `https://batoohan.ru/admin/` - должна загрузиться админ-панель без ошибок.

### Проверка сайта:
Откройте `https://batoohan.ru` - сайт должен загружаться, форма обратной связи и форма покупки должны работать.

## Дополнительные замечания

- Убедитесь, что директория `/var/www/dnk` существует и содержит файлы сайта
- Убедитесь, что порты 8001 и 8080 не заняты другими процессами
- При первом запуске Telegram-бота проверьте, что в `.env` заполнены `TELEGRAM_BOT_TOKEN`, `ADMIN_CHAT_ID` и другие переменные
- Проверьте, что SSL сертификаты настроены правильно (или используйте самоподписанные для тестирования)

