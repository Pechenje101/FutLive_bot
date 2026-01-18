#!/bin/bash

# FutLive Player V2 - VPS Setup Script
# Этот скрипт настраивает VPS для развертывания проекта

set -e

echo "🚀 FutLive Player V2 - VPS Setup"
echo "=================================="

# Проверка прав администратора
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен быть запущен с правами sudo"
   exit 1
fi

# 1. Обновление системы
echo "📦 Обновление системы..."
apt-get update
apt-get upgrade -y

# 2. Установка необходимых пакетов
echo "📦 Установка зависимостей..."
apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx

# 3. Установка Docker
echo "🐳 Установка Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# 4. Установка Docker Compose
echo "🐳 Установка Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 5. Установка Node.js
echo "📦 Установка Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs

# 6. Установка pnpm
echo "📦 Установка pnpm..."
npm install -g pnpm

# 7. Создание директории проекта
echo "📁 Создание директории проекта..."
mkdir -p /home/ubuntu/futlive-player-v2
cd /home/ubuntu/futlive-player-v2

# 8. Клонирование репозитория
echo "📥 Клонирование репозитория..."
read -p "Введите URL вашего GitHub репозитория: " REPO_URL
git clone $REPO_URL .

# 9. Установка зависимостей
echo "📦 Установка зависимостей проекта..."
pnpm install

# 10. Создание .env файла
echo "⚙️  Создание .env файла..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Отредактируйте .env файл с вашими конфигурациями!"
    echo "   Важные переменные:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - SENTRY_DSN"
    echo "   - DOMAIN_NAME"
fi

# 11. Настройка Redis
echo "🔴 Настройка Redis..."
systemctl enable redis-server
systemctl start redis-server

# 12. Настройка Nginx
echo "🌐 Настройка Nginx..."
cp nginx.conf /etc/nginx/sites-available/futlive-player
ln -sf /etc/nginx/sites-available/futlive-player /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# 13. Получение SSL сертификата
echo "🔒 Получение SSL сертификата..."
read -p "Введите ваш домен (например: futlive.example.com): " DOMAIN_NAME
certbot certonly --nginx -d $DOMAIN_NAME --non-interactive --agree-tos -m admin@$DOMAIN_NAME

# 14. Запуск Docker контейнеров
echo "🐳 Запуск Docker контейнеров..."
docker-compose up -d

# 15. Проверка статуса
echo "✅ Проверка статуса..."
docker-compose ps

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте .env файл с вашими конфигурациями"
echo "2. Проверьте статус: docker-compose ps"
echo "3. Просмотрите логи: docker-compose logs -f"
echo "4. Откройте https://$DOMAIN_NAME в браузере"
echo ""
echo "📚 Документация: https://github.com/yourusername/futlive-player-v2"
