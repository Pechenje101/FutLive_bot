#!/bin/bash

# FutLive Player V2 - Скрипт для запуска всех компонентов
# Использование: ./start_all.sh

set -e

PROJECT_DIR="/home/ubuntu/futlive-player-v2"
LOG_DIR="$PROJECT_DIR/logs"

# Создаем директорию для логов
mkdir -p "$LOG_DIR"

echo "🚀 FutLive Player V2 - Запуск всех компонентов"
echo "================================================"

# Функция для запуска процесса в фоне с логированием
run_service() {
    local name=$1
    local command=$2
    local log_file="$LOG_DIR/${name}.log"
    
    echo "📍 Запуск $name..."
    eval "$command" > "$log_file" 2>&1 &
    local pid=$!
    echo "✅ $name запущен (PID: $pid)"
    echo "$pid" > "$LOG_DIR/${name}.pid"
}

# Проверка зависимостей
echo ""
echo "🔍 Проверка зависимостей..."

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    exit 1
fi
echo "✅ Python3 найден"

# Проверка Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не установлен"
    exit 1
fi
echo "✅ Node.js найден"

# Проверка pnpm
if ! command -v pnpm &> /dev/null; then
    echo "❌ pnpm не установлен"
    exit 1
fi
echo "✅ pnpm найден"

# Установка Python зависимостей
echo ""
echo "📦 Установка Python зависимостей..."
pip3 install -q flask flask-cors requests beautifulsoup4 aiogram 2>/dev/null || true

# Установка Node.js зависимостей
echo "📦 Установка Node.js зависимостей..."
cd "$PROJECT_DIR"
pnpm install --frozen-lockfile 2>/dev/null || true

echo ""
echo "🔄 Запуск компонентов..."
echo "========================"

# Запуск API сервера
run_service "api-server" "cd $PROJECT_DIR && python3 api_server.py"
sleep 2

# Запуск Web App dev сервера
run_service "web-app" "cd $PROJECT_DIR && pnpm run dev"
sleep 3

# Запуск Telegram Bot
run_service "telegram-bot" "cd $PROJECT_DIR && python3 bot_final.py"
sleep 2

echo ""
echo "✅ Все компоненты запущены!"
echo "=========================="
echo ""
echo "📊 Статус сервисов:"
echo "  🤖 Telegram Bot: Запущен"
echo "  🌐 Web App: http://localhost:3000"
echo "  📡 API Server: http://localhost:5000"
echo ""
echo "📝 Логи находятся в: $LOG_DIR"
echo ""
echo "🔗 Ссылки:"
echo "  - Telegram Bot: @FutLiveBot (найти в Telegram)"
echo "  - Web App: https://futlive-player-v2.manus.space"
echo "  - API Docs: http://localhost:5000/api/health"
echo ""
echo "⏹️  Для остановки всех сервисов выполните: ./stop_all.sh"
echo ""

# Показываем логи в реальном времени
echo "📺 Логи (Ctrl+C для выхода):"
echo "================================"
tail -f "$LOG_DIR"/*.log
