# Руководство по развертыванию в Production

## Обзор

Это руководство описывает процесс развертывания приложения на production сервере `batoohan.ru` с использованием Docker, Nginx и SSL сертификатов.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (на хосте)                          │
│  - Статический сайт (dnk/) на /                             │
│  - API проксирование на /api/ → Docker контейнер api:8000   │
│  - Админ-панель на /admin/ → Docker контейнер frontend:8080 │
│  - Загрузки на /uploads/ → Docker контейнер api:8000        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼────────┐
│  Docker API    │                    │ Docker Frontend │
│  (порт 8000)   │                    │  (порт 8080)    │
│                │                    │                 │
│  - FastAPI     │                    │  - React App    │
│  - SQLite DB   │                    │  - Nginx        │
│  - Uploads     │                    │                 │
└────────────────┘                    └─────────────────┘
```

## Требования

- Ubuntu Server 24.04
- Docker и Docker Compose
- Nginx
- Certbot (для SSL сертификатов)
- Домен `batoohan.ru` с настроенным DNS

## Подготовка

### 1. Установка зависимостей

См. раздел "Деплой через Docker (Ubuntu Server 24.04)" в `SETUP_GUIDE.md`.

### 2. Настройка окружения

1. Скопируйте `.env.example` в `.env`
2. Заполните все необходимые переменные (см. комментарии в `.env.example`)
3. Установите `ENVIRONMENT=production`
4. Обязательно измените `ADMIN_USERNAME` и `ADMIN_PASSWORD`!

### 3. Подготовка статического сайта

Скопируйте папку `dnk/` на сервер в `/var/www/batoohan.ru/`:

```bash
# На локальной машине
scp -r dnk/* user@server:/var/www/batoohan.ru/
```

Или используйте `rsync`:

```bash
rsync -avz dnk/ user@server:/var/www/batoohan.ru/
```

### 4. Настройка Nginx

1. Скопируйте конфигурацию:
   ```bash
   sudo cp nginx/nginx.production.conf /etc/nginx/sites-available/batoohan.ru
   ```

2. Активируйте конфигурацию:
   ```bash
   sudo ln -s /etc/nginx/sites-available/batoohan.ru /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### 5. Получение SSL сертификата

```bash
sudo certbot --nginx -d batoohan.ru -d www.batoohan.ru
```

Certbot автоматически обновит конфигурацию nginx с правильными путями к сертификатам.

### 6. Запуск Docker контейнеров

```bash
cd /opt/fitness-crm
docker compose -f docker-compose.production.yml up -d --build
```

## Проверка

1. **Сайт**: https://www.batoohan.ru
2. **API**: https://www.batoohan.ru/api/health (если настроена)
3. **Админ-панель**: https://www.batoohan.ru/admin/
4. **Логи**: `docker compose -f docker-compose.production.yml logs -f`

## Обслуживание

### Обновление приложения

```bash
cd /opt/fitness-crm
git pull
docker compose -f docker-compose.production.yml up -d --build
```

### Резервное копирование

```bash
# База данных
docker compose -f docker-compose.production.yml exec api cp /data/crm.db /tmp/crm.db
docker compose -f docker-compose.production.yml cp api:/tmp/crm.db ~/backups/crm_$(date +%Y%m%d).db

# Загрузки
tar -czf ~/backups/uploads_$(date +%Y%m%d).tar.gz uploads/

# Статический сайт
tar -czf ~/backups/site_$(date +%Y%m%d).tar.gz /var/www/batoohan.ru/
```

### Мониторинг

```bash
# Логи контейнеров
docker compose -f docker-compose.production.yml logs -f

# Логи Nginx
sudo tail -f /var/log/nginx/batoohan.ru.access.log
sudo tail -f /var/log/nginx/batoohan.ru.error.log

# Статус контейнеров
docker compose -f docker-compose.production.yml ps

# Использование ресурсов
docker stats
```

## Устранение неполадок

### Контейнеры не запускаются

1. Проверьте логи: `docker compose -f docker-compose.production.yml logs`
2. Проверьте конфигурацию: `docker compose -f docker-compose.production.yml config`
3. Пересоберите без кэша: `docker compose -f docker-compose.production.yml build --no-cache`

### Nginx не проксирует запросы

1. Проверьте конфигурацию: `sudo nginx -t`
2. Проверьте, что контейнеры работают: `docker compose -f docker-compose.production.yml ps`
3. Проверьте порты: `sudo netstat -tulpn | grep -E '8000|8080'`
4. Проверьте логи: `sudo tail -f /var/log/nginx/batoohan.ru.error.log`

### Проблемы с SSL

1. Обновите сертификат: `sudo certbot renew`
2. Проверьте статус: `sudo certbot certificates`

## Безопасность

1. **Измените пароль администратора** после первого входа
2. **Используйте сильные пароли** для всех сервисов
3. **Регулярно обновляйте** систему и зависимости
4. **Настройте файрвол** (UFW) для ограничения доступа
5. **Регулярно делайте резервные копии** базы данных и файлов
6. **Мониторьте логи** на наличие подозрительной активности

## Дополнительная информация

- Подробные инструкции по установке: `SETUP_GUIDE.md`
- Руководство администратора: `docs/ADMIN_GUIDE.md`
- Руководство пользователя: `docs/USER_GUIDE.md`

