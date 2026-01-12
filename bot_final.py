#!/usr/bin/env python3
"""
FutLive Bot - Telegram бот для просмотра футбольных трансляций
Интегрирован с Web App плеером на базе Video.js
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
sys.path.insert(0, '/home/ubuntu')

from parser import get_matches, get_match_links

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
API_TOKEN = "8111388773:AAFiCTukv5d8XSavnsL7ybMs8kRL42uFWB4"
WEB_APP_URL = "https://futlive-player-v2.manus.space/player"  # URL вашего Web App

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Состояния FSM
class MatchSelection(StatesGroup):
    waiting_for_match = State()
    loading_channels = State()

# Кэш матчей
matches_cache = {}
cache_timestamp = 0
CACHE_DURATION = 300  # 5 минут

async def get_cached_matches():
    """Получить матчи с кэшированием"""
    global matches_cache, cache_timestamp
    import time
    
    current_time = time.time()
    if matches_cache and (current_time - cache_timestamp) < CACHE_DURATION:
        return matches_cache
    
    try:
        matches = await get_matches()
        matches_cache = matches
        cache_timestamp = current_time
        return matches
    except Exception as e:
        logger.error(f"Ошибка при получении матчей: {e}")
        return []

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    welcome_text = (
        "⚽ <b>FutLive - Просмотр футбольных трансляций</b>\n\n"
        "Выберите матч из списка ниже, и я покажу вам доступные каналы для просмотра.\n\n"
        "💡 <i>Трансляции открываются прямо в Telegram через встроенный плеер</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ Список матчей", callback_data="list_matches")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_matches")],
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "list_matches")
async def list_matches(query: types.CallbackQuery, state: FSMContext):
    """Показать список доступных матчей"""
    await query.answer("Загружаю матчи...", show_alert=False)
    
    try:
        matches = await get_cached_matches()
        
        if not matches:
            await query.message.edit_text(
                "❌ Матчи не найдены. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_matches")],
                ])
            )
            return
        
        # Создаем кнопки для каждого матча
        keyboard_buttons = []
        for idx, match in enumerate(matches[:20]):  # Ограничиваем до 20 матчей
            button_text = f"⚽ {match['title'][:30]}"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"match_{idx}"
                )
            ])
        
        # Добавляем кнопку обновления
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_matches")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = f"📺 <b>Доступные матчи ({len(matches)})</b>\n\nВыберите матч для просмотра:"
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке матчей: {e}")
        await query.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_matches")],
            ])
        )

@dp.callback_query(F.data.startswith("match_"))
async def select_match(query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора матча"""
    match_idx = int(query.data.split("_")[1])
    
    try:
        matches = await get_cached_matches()
        
        if match_idx >= len(matches):
            await query.answer("❌ Матч не найден", show_alert=True)
            return
        
        match = matches[match_idx]
        
        # Сохраняем индекс матча в состояние
        await state.update_data(match_index=match_idx)
        
        # Создаем Web App кнопку для открытия плеера
        web_app_button = InlineKeyboardButton(
            text="📱 Смотреть в приложении",
            web_app=WebAppInfo(url=f"{WEB_APP_URL}?match_id={match_idx}")
        )
        
        # Получаем информацию о каналах
        try:
            links = await get_match_links(match['url'])
            channels_info = f"\n\n📊 <b>Доступные каналы:</b>\n"
            
            for channel_name, channel_url in links.items():
                if channel_url.startswith('acestream://'):
                    channels_info += f"🎬 {channel_name}\n"
                else:
                    channels_info += f"🌐 {channel_name}\n"
            
        except Exception as e:
            logger.warning(f"Ошибка при получении ссылок: {e}")
            channels_info = "\n\n⚠️ Информация о каналах недоступна"
        
        text = (
            f"<b>⚽ {match['title']}</b>\n"
            f"🔗 <a href='{match['url']}'>Оригинальная страница</a>"
            f"{channels_info}\n\n"
            f"<i>Нажмите кнопку ниже для просмотра в приложении</i>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [web_app_button],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_matches")],
        ])
        
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе матча: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.callback_query(F.data == "refresh_matches")
async def refresh_matches(query: types.CallbackQuery):
    """Обновить кэш матчей"""
    global matches_cache, cache_timestamp
    matches_cache = {}
    cache_timestamp = 0
    
    await query.answer("🔄 Кэш очищен, загружаю свежие матчи...", show_alert=False)
    await list_matches(query, FSMContext(storage=None, key=None))

@dp.message()
async def handle_message(message: types.Message):
    """Обработка остальных сообщений"""
    await message.answer(
        "Используйте команду /start для начала работы",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать", callback_data="list_matches")],
        ])
    )

async def main():
    """Запуск бота"""
    logger.info("🤖 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
