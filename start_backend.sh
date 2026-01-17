#!/bin/bash

# Запуск API сервера через Gunicorn для production
echo "🚀 Запуск API сервера..."
gunicorn --bind 0.0.0.0:5000 --workers 3 --timeout 120 api_server:app &

# Запуск Telegram бота
echo "🤖 Запуск Telegram бота..."
python3 bot_final.py &

# Ожидание завершения процессов
wait
