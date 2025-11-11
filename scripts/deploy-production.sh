#!/bin/bash
# Скрипт для развертывания приложения на production сервере
# Использование: ./scripts/deploy-production.sh

set -e  # Остановка при ошибке

echo "🚀 Начало развертывания на production..."

# Проверка, что мы в правильной директории
if [ ! -f "docker-compose.production.yml" ]; then
    echo "❌ Ошибка: файл docker-compose.production.yml не найден"
    echo "Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Создайте его из .env.example"
    echo "cp .env.example .env"
    echo "nano .env"
    exit 1
fi

# Проверка, что ENVIRONMENT=production
if ! grep -q "ENVIRONMENT=production" .env; then
    echo "⚠️  Предупреждение: ENVIRONMENT не установлен в production"
    echo "Рекомендуется установить ENVIRONMENT=production в .env"
fi

echo "📦 Сборка и запуск контейнеров..."
docker compose -f docker-compose.production.yml build --no-cache
docker compose -f docker-compose.production.yml up -d

echo "⏳ Ожидание запуска контейнеров..."
sleep 10

echo "🔍 Проверка статуса контейнеров..."
docker compose -f docker-compose.production.yml ps

echo "📋 Последние логи API:"
docker compose -f docker-compose.production.yml logs --tail=50 api

echo "📋 Последние логи Frontend:"
docker compose -f docker-compose.production.yml logs --tail=50 frontend

echo "✅ Развертывание завершено!"
echo ""
echo "Проверьте:"
echo "  - Сайт: https://www.batoohan.ru"
echo "  - API: https://www.batoohan.ru/api/health"
echo "  - Админ-панель: https://www.batoohan.ru/admin/"
echo ""
echo "Для просмотра логов:"
echo "  docker compose -f docker-compose.production.yml logs -f"

