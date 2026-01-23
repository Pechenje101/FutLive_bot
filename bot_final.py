"""
FutLive Bot - Telegram бот для просмотра футбольных трансляций
Матчи: gooool365.org
Трансляции: livetv.sx
"""

import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
sys.path.insert(0, '/home/ubuntu/futlive-player-v2')

from parser_async import get_matches
from redis_cache import get_cache

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8111388773:AAFiCTukv5d8XSavnsL7ybMs8kRL42uFWB4")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Инициализация сервисов
cache = get_cache()

# Состояния FSM
class MatchSelection(StatesGroup):
    waiting_for_match = State()
    loading_channels = State()

async def get_cached_matches():
    """Получить матчи с Redis кэшированием"""
    try:
        # Сначала проверяем кэш
        cached = cache.get_matches()
        if cached:
            logger.info(f"📦 Матчи получены из кэша ({len(cached)} шт)")
            return cached
        
        # Если кэша нет, загружаем из парсера
        logger.info("🔄 Загрузка матчей из gooool365.org...")
        matches = await get_matches()
        
        # Сохраняем в кэш
        if matches:
            cache.set_matches(matches, ttl=300)  # 5 минут
            logger.info(f"✅ Загружено {len(matches)} матчей")
        
        return matches
    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчей: {e}")
        return []

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    welcome_text = (
        "⚽ <b>FutLive - Просмотр футбольных трансляций</b>\n\n"
        "Выберите матч из списка ниже, и я покажу вам доступные трансляции.\n\n"
        "📺 <i>Трансляции открываются на livetv.sx</i>\n\n"
        "🔍 <i>Матчи загружаются с gooool365.org</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список матчей", callback_data="list_matches")],
        [InlineKeyboardButton(text="❓ Справка", callback_data="help")],
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"👤 Пользователь {message.from_user.id} запустил бота")

@dp.callback_query(F.data == "list_matches")
async def show_matches(callback: types.CallbackQuery, state: FSMContext):
    """Показать список матчей"""
    await callback.answer()
    await state.set_state(MatchSelection.loading_channels)
    
    # Отправляем сообщение о загрузке
    loading_msg = await callback.message.answer("⏳ Загружаю матчи...")
    
    try:
        matches = await get_cached_matches()
        
        if not matches:
            await loading_msg.edit_text(
                "❌ Матчи не найдены. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="list_matches")],
                ])
            )
            return
        
        # Создаем клавиатуру с матчами (максимум 10)
        keyboard_buttons = []
        for i, match in enumerate(matches[:10]):
            match_name = match.get('name', 'Unknown')[:30]  # Ограничиваем длину
            callback_data = f"match_{i}"
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⚽ {match_name}", callback_data=callback_data)
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔄 Обновить", callback_data="list_matches")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = (
            f"📋 <b>Найдено {len(matches)} матчей</b>\n\n"
            "Выберите матч для просмотра трансляции:"
        )
        
        await loading_msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(MatchSelection.waiting_for_match)
        
        # Сохраняем матчи в контекст
        await state.update_data(matches=matches)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке матчей: {e}")
        await loading_msg.edit_text(
            f"❌ Ошибка: {str(e)[:100]}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="list_matches")],
            ])
        )

@dp.callback_query(F.data.startswith("match_"))
async def show_match_streams(callback: types.CallbackQuery, state: FSMContext):
    """Показать трансляции для выбранного матча"""
    await callback.answer()
    
    try:
        # Получаем индекс матча
        match_index = int(callback.data.split("_")[1])
        
        # Получаем матчи из контекста
        data = await state.get_data()
        matches = data.get('matches', [])
        
        if match_index >= len(matches):
            await callback.message.answer("❌ Матч не найден")
            return
        
        match = matches[match_index]
        match_name = match.get('name', 'Unknown')
        match_time = match.get('time', 'Unknown')
        
        # Формируем ссылку на livetv.sx для поиска матча
        search_query = match_name.replace(' - ', ' ').replace(' ', '+')
        livetv_search_url = f"https://livetv.sx/search/?q={search_query}"
        
        text = (
            f"📺 <b>Трансляция</b>\n\n"
            f"⚽ <b>{match_name}</b>\n"
            f"⏰ <b>{match_time}</b>\n\n"
            f"<i>Нажмите кнопку ниже для поиска трансляции на livetv.sx</i>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📺 Смотреть на livetv.sx", url=livetv_search_url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_matches")],
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при показе трансляций: {e}")
        await callback.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    """Показать справку"""
    await callback.answer()
    
    help_text = (
        "❓ <b>Справка</b>\n\n"
        "<b>Как использовать бота:</b>\n"
        "1️⃣ Нажмите кнопку 'Список матчей'\n"
        "2️⃣ Выберите интересующий вас матч\n"
        "3️⃣ Нажмите кнопку 'Смотреть на livetv.sx' для открытия трансляции\n\n"
        "<b>Источники данных:</b>\n"
        "📋 Матчи: gooool365.org\n"
        "📺 Трансляции: livetv.sx\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать\n"
        "/help - Справка\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_matches")],
    ])
    
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Обработка команды /help"""
    help_text = (
        "❓ <b>Справка</b>\n\n"
        "<b>Как использовать бота:</b>\n"
        "1️⃣ Нажмите кнопку 'Список матчей'\n"
        "2️⃣ Выберите интересующий вас матч\n"
        "3️⃣ Нажмите кнопку 'Смотреть на livetv.sx' для открытия трансляции\n\n"
        "<b>Источники данных:</b>\n"
        "📋 Матчи: gooool365.org\n"
        "📺 Трансляции: livetv.sx\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать\n"
        "/help - Справка\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список матчей", callback_data="list_matches")],
    ])
    
    await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message()
async def echo(message: types.Message):
    """Обработка остальных сообщений"""
    await message.answer(
        "👋 Привет! Используйте команду /start для начала работы.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать", callback_data="list_matches")],
        ])
    )

async def main():
    """Главная функция"""
    logger.info("🤖 Запуск FutLive Bot...")
    logger.info(f"📡 API Token: {API_TOKEN[:20]}...")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
