#!/bin/bash

# Скрипт для быстрого развертывания FutLive Player V2
# Использование: ./deploy.sh your-domain.com your-email@example.com your-telegram-token

set -e

DOMAIN=${1:-futlive.example.com}
EMAIL=${2:-admin@example.com}
TELEGRAM_TOKEN=${3:-}

echo "🚀 Развертывание FutLive Player V2"
echo "=================================="
echo "Домен: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p certbot/conf certbot/www logs

# Создание .env файла
echo "⚙️ Создание конфигурации..."
cat > .env << EOF
TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN
API_URL=https://$DOMAIN
FLASK_ENV=production
REDIS_HOST=redis
REDIS_PORT=6379
DOMAIN=$DOMAIN
EMAIL=$EMAIL
APP_VERSION=1.0.0
EOF

echo "✅ .env файл создан"
echo ""
echo "⚠️  ВАЖНО: Отредактируйте .env файл и добавьте:"
echo "   - TELEGRAM_BOT_TOKEN (если еще не добавлен)"
echo "   - SENTRY_DSN (опционально)"
echo ""
echo "Затем запустите:"
echo "  1. docker-compose build"
echo "  2. docker-compose up -d"
echo ""
echo "Для получения SSL сертификата запустите:"
echo "  docker run -it --rm -v \$(pwd)/certbot/conf:/etc/letsencrypt \\"
echo "    -v \$(pwd)/certbot/www:/var/www/certbot \\"
echo "    certbot/certbot certonly --webroot \\"
echo "    -w /var/www/certbot \\"
echo "    -d $DOMAIN \\"
echo "    --email $EMAIL \\"
echo "    --agree-tos \\"
echo "    --non-interactive"
