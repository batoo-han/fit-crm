# Конфигурация Nginx для Production

## Описание

Эта папка содержит конфигурацию Nginx для развертывания приложения на production сервере `batoohan.ru`.

## Структура

- `nginx.production.conf` - основная конфигурация Nginx для production

## Установка

1. Скопируйте конфигурацию на сервер:
   ```bash
   sudo cp nginx.production.conf /etc/nginx/sites-available/batoohan.ru
   ```

2. Создайте симлинк:
   ```bash
   sudo ln -s /etc/nginx/sites-available/batoohan.ru /etc/nginx/sites-enabled/
   ```

3. Проверьте конфигурацию:
   ```bash
   sudo nginx -t
   ```

4. Перезагрузите Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

## Настройка SSL

После установки конфигурации получите SSL сертификат через Certbot:

```bash
sudo certbot --nginx -d batoohan.ru -d www.batoohan.ru
```

Certbot автоматически обновит конфигурацию с правильными путями к сертификатам.

## Архитектура

Nginx на сервере обслуживает:

1. **Статический сайт** (`/var/www/batoohan.ru/`) - основной сайт на корневом пути `/`
2. **API** (`/api/`) - проксирование на Docker контейнер `api:8000`
3. **Админ-панель** (`/admin/`) - проксирование на Docker контейнер `frontend:8080`
4. **Загрузки** (`/uploads/`) - проксирование на Docker контейнер `api:8000`

## Требования

- Docker контейнеры должны быть запущены и доступны на `127.0.0.1:8000` (API) и `127.0.0.1:8080` (Frontend)
- Статический сайт должен быть развернут в `/var/www/batoohan.ru/`
- SSL сертификаты должны быть получены через Certbot

## Логи

Логи Nginx находятся в:
- `/var/log/nginx/batoohan.ru.access.log` - access log
- `/var/log/nginx/batoohan.ru.error.log` - error log

## Обслуживание

После изменения конфигурации:
1. Проверьте синтаксис: `sudo nginx -t`
2. Перезагрузите Nginx: `sudo systemctl reload nginx`

## Безопасность

Конфигурация включает:
- SSL/TLS шифрование
- Заголовки безопасности (X-Frame-Options, X-Content-Type-Options, и т.д.)
- Запрет доступа к скрытым файлам и конфигурационным файлам
- Ограничение размера загружаемых файлов (50M)

