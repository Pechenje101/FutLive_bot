#!/bin/bash

# FutLive Player V2 - Скрипт для остановки всех компонентов
# Использование: ./stop_all.sh

PROJECT_DIR="/home/ubuntu/futlive-player-v2"
LOG_DIR="$PROJECT_DIR/logs"

echo "🛑 FutLive Player V2 - Остановка всех компонентов"
echo "=================================================="

# Функция для остановки процесса
stop_service() {
    local name=$1
    local pid_file="$LOG_DIR/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "⏹️  Остановка $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
            echo "✅ $name остановлен"
        else
            echo "⚠️  $name не запущен (PID файл: $pid_file)"
            rm -f "$pid_file"
        fi
    else
        echo "⚠️  PID файл не найден для $name"
    fi
}

# Остановка всех сервисов
stop_service "telegram-bot"
stop_service "web-app"
stop_service "api-server"

echo ""
echo "✅ Все компоненты остановлены!"
echo ""

# Альтернативный способ - убить все процессы Python и Node
echo "💡 Если сервисы все еще запущены, используйте:"
echo "   pkill -f 'python3.*bot_final.py'"
echo "   pkill -f 'python3.*api_server.py'"
echo "   pkill -f 'vite'"
