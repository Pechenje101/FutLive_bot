#!/bin/bash

# Скрипт для запуска Redis сервера

echo "🚀 Запуск Redis сервера..."

# Проверяем, установлен ли Redis
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis не установлен. Установите его командой:"
    echo "   sudo apt-get install redis-server"
    exit 1
fi

# Запускаем Redis в фоне
redis-server --daemonize yes --logfile /home/ubuntu/futlive-player-v2/logs/redis.log

# Проверяем, запустился ли Redis
sleep 1
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis успешно запущен"
    echo "📊 Статус Redis:"
    redis-cli info server | grep redis_version
else
    echo "❌ Ошибка при запуске Redis"
    exit 1
fi
