"""
Обновленный бот FutLive с интеграцией нового Web App плеера
Готов к развертыванию и тестированию
"""

import asyncio
import logging
from datetime import datetime, timedelta
import json
import sys
import os

# Добавляем путь к парсеру
sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем парсер (предполагаем, что он находится в том же каталоге)
try:
    from parser import get_matches, get_streams
except ImportError:
    print("⚠️ Парсер не найден. Используем mock данные для тестирования.")
    get_matches = None
    get_streams = None

# Конфигурация
API_TOKEN = "8111388773:AAFiCTukv5d8XSavnsL7ybMs8kRL42uFWB4"
WEB_APP_URL = "https://futlive-player-v2.manus.space"  # URL вашего Web App

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Кэш для матчей
class MatchCache:
    def __init__(self, ttl_minutes=30, max_size=100):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            del self.cache[key]
        return None
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]
        self.cache[key] = (value, datetime.now())
    
    def clear_old(self):
        now = datetime.now()
        expired = [k for k, (_, t) in self.cache.items() if now - t > self.ttl]
        for k in expired:
            del self.cache[k]

match_cache = MatchCache()

# Mock данные для тестирования (если парсер недоступен)
MOCK_MATCHES = [
    {
        "title": "Эвертон - Сандерленд",
        "url": "https://gooool365.org/online/191987-jeverton-sanderlend-10-janvarja-prjamaja-transljacija.html",
        "channels": [
            {"title": "Setanta Sports 1 HD", "url": "acestream://c58ddd8c6bb963fa78e6f79d2e3c6a15d93f8241"},
            {"title": "DAZN 2 HD", "url": "acestream://12ea555dd31dbe51fc8e4ca745aec09fe22a4865"},
        ]
    },
    {
        "title": "Манчестер Сити - Челси",
        "url": "https://gooool365.org/online/test-match-2.html",
        "channels": [
            {"title": "Sky Sports 1", "url": "https://example.com/stream1"},
            {"title": "BT Sport", "url": "https://example.com/stream2"},
        ]
    },
]

async def get_matches_async():
    """Получить матчи с кэшированием"""
    cached = match_cache.get('matches')
    if cached:
        logger.info("Используем кэшированные матчи")
        return cached
    
    try:
        if get_matches:
            logger.info("Парсим матчи с сайта...")
            matches = await asyncio.to_thread(get_matches)
            match_cache.set('matches', matches)
            return matches
        else:
            logger.warning("Парсер недоступен, используем mock данные")
            return MOCK_MATCHES
    except Exception as e:
        logger.error(f"Ошибка при парсинге матчей: {e}")
        cached = match_cache.get('matches')
        return cached or MOCK_MATCHES

async def get_streams_async(match_url):
    """Получить потоки для матча"""
    try:
        if get_streams:
            logger.info(f"Получаем потоки для: {match_url}")
            streams = await asyncio.to_thread(get_streams, match_url)
            return streams
        else:
            return []
    except Exception as e:
        logger.error(f"Ошибка при получении потоков: {e}")
        return []

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """Команда /start - показать список матчей"""
    try:
        await message.answer(
            "⚽ <b>FutLive - Просмотр футбольных трансляций</b>\n\n"
            "Загружаю список матчей...",
            parse_mode="HTML"
        )
        
        matches = await get_matches_async()
        
        if not matches:
            await message.answer(
                "❌ Матчи не найдены. Попробуйте позже.",
                parse_mode="HTML"
            )
            return
        
        # Создаем кнопки для матчей
        builder = InlineKeyboardBuilder()
        
        for i, match in enumerate(matches[:10]):  # Максимум 10 матчей
            title = match.get('title', f'Матч {i+1}')[:30]  # Ограничиваем длину
            builder.button(
                text=f"⚽ {title}",
                callback_data=f"match_{i}"
            )
        
        builder.adjust(1)  # Одна кнопка в ряд
        
        await message.answer(
            "📺 <b>Доступные матчи:</b>\n\n"
            "Выберите матч для просмотра:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

@dp.callback_query_handler(lambda c: c.data.startswith('match_'))
async def handle_match_selection(callback: types.CallbackQuery):
    """Обработка выбора матча"""
    try:
        match_index = int(callback.data.split('_')[1])
        matches = await get_matches_async()
        
        if match_index >= len(matches):
            await callback.answer("❌ Матч не найден", show_alert=True)
            return
        
        match = matches[match_index]
        match_title = match.get('title', 'Матч')
        match_url = match.get('url', '')
        
        # Получаем потоки для матча
        streams = match.get('channels', [])
        if not streams and match_url and get_streams:
            streams = await get_streams_async(match_url)
        
        # Если потоков нет, используем mock
        if not streams:
            streams = [
                {"title": "Канал 1", "url": "https://example.com/stream1"},
                {"title": "Канал 2", "url": "https://example.com/stream2"},
            ]
        
        # Создаем кнопки для каналов
        builder = InlineKeyboardBuilder()
        
        for i, channel in enumerate(streams[:5]):  # Максимум 5 каналов
            channel_title = channel.get('title', f'Канал {i+1}')[:20]
            builder.button(
                text=f"📺 {channel_title}",
                web_app=WebAppInfo(
                    url=f"{WEB_APP_URL}/player?match_id={match_index}&channel={i}&title={match_title}"
                )
            )
        
        builder.adjust(1)  # Одна кнопка в ряд
        
        await callback.message.edit_text(
            f"<b>⚽ {match_title}</b>\n\n"
            f"📊 Доступно каналов: {len(streams)}\n\n"
            "Выберите канал для просмотра:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_match_selection: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'back')
async def handle_back(callback: types.CallbackQuery):
    """Вернуться к списку матчей"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "⚽ <b>FutLive - Просмотр футбольных трансляций</b>\n\n"
            "Загружаю список матчей...",
            parse_mode="HTML"
        )
        
        matches = await get_matches_async()
        
        if not matches:
            await callback.message.answer("❌ Матчи не найдены.")
            return
        
        builder = InlineKeyboardBuilder()
        
        for i, match in enumerate(matches[:10]):
            title = match.get('title', f'Матч {i+1}')[:30]
            builder.button(
                text=f"⚽ {title}",
                callback_data=f"match_{i}"
            )
        
        builder.adjust(1)
        
        await callback.message.answer(
            "📺 <b>Доступные матчи:</b>\n\n"
            "Выберите матч для просмотра:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_back: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    """Команда /help"""
    await message.answer(
        "<b>📺 FutLive - Помощь</b>\n\n"
        "/start - Показать список матчей\n"
        "/help - Показать эту справку\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Нажмите /start\n"
        "2. Выберите матч\n"
        "3. Выберите канал\n"
        "4. Смотрите трансляцию в плеере\n\n"
        "✅ Поддерживаемые форматы:\n"
        "• Ace Stream (acestream://)\n"
        "• HTTP потоки\n"
        "• Web плееры",
        parse_mode="HTML"
    )

async def main():
    """Запуск бота"""
    logger.info("🚀 Запуск бота FutLive...")
    logger.info(f"Web App URL: {WEB_APP_URL}")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
