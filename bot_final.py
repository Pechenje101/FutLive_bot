#!/usr/bin/env python3
"""
FutLive Bot - Telegram бот для просмотра футбольных трансляций
Интегрирован с Web App плеером на базе Video.js
Поддерживает Redis кэширование и уведомления о матчах
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
sys.path.insert(0, '/home/ubuntu/futlive-player-v2')

from parser_async import get_matches, get_match_links
from redis_cache import get_cache
from notifications_service import get_notification_service

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
API_TOKEN = "8111388773:AAFiCTukv5d8XSavnsL7ybMs8kRL42uFWB4"
WEB_APP_URL = "https://futlive-player-v2.manus.space/player"
API_BASE_URL = "https://futlive-player-v2.manus.space/api"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Инициализация сервисов
cache = get_cache()
notification_service = get_notification_service()

# Состояния FSM
class MatchSelection(StatesGroup):
    waiting_for_match = State()
    loading_channels = State()
    waiting_for_reminder = State()

async def get_cached_matches():
    """Получить матчи с Redis кэшированием"""
    try:
        # Сначала проверяем кэш
        cached = cache.get_matches()
        if cached:
            logger.info(f"📦 Матчи получены из кэша ({len(cached)} шт)")
            return cached
        
        # Если кэша нет, загружаем из парсера
        logger.info("🔄 Загрузка матчей из парсера...")
        matches = await get_matches()
        
        # Сохраняем в кэш
        if matches:
            cache.set_matches(matches, ttl=300)  # 5 минут
        
        return matches
    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчей: {e}")
        return []

async def send_notification(notification: dict):
    """Отправить уведомление пользователю"""
    try:
        user_id = notification['user_id']
        match_title = notification['match_title']
        
        text = (
            f"🔔 <b>Напоминание о матче!</b>\n\n"
            f"⚽ <b>{match_title}</b>\n"
            f"⏰ Матч начинается через 15 минут!\n\n"
            f"<i>Нажмите кнопку ниже для просмотра</i>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📺 Смотреть матч", callback_data="list_matches")],
        ])
        
        await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"✅ Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомления: {e}")

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    welcome_text = (
        "⚽ <b>FutLive - Просмотр футбольных трансляций</b>\n\n"
        "Выберите матч из списка ниже, и я покажу вам доступные каналы для просмотра.\n\n"
        "💡 <i>Трансляции открываются прямо в Telegram через встроенный плеер</i>\n\n"
        "🔔 <i>Вы можете подписаться на напоминания за 15 минут до матча</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚽ Список матчей", callback_data="list_matches")],
        [InlineKeyboardButton(text="⭐ Мои избранные", callback_data="my_favorites")],
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
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
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
        
        # Добавляем кнопки управления
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_matches")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = f"📺 <b>Доступные матчи ({len(matches)})</b>\n\nВыберите матч для просмотра:"
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке матчей: {e}")
        await query.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_matches")],
            ])
        )

@dp.callback_query(F.data == "my_favorites")
async def my_favorites(query: types.CallbackQuery):
    """Показать избранные матчи"""
    try:
        user_id = query.from_user.id
        favorites = cache.get_favorites(user_id)
        
        if not favorites:
            await query.answer("У вас нет избранных матчей", show_alert=True)
            return
        
        matches = await get_cached_matches()
        
        # Создаем кнопки для избранных матчей
        keyboard_buttons = []
        for match_id in favorites:
            if match_id < len(matches):
                match = matches[match_id]
                button_text = f"⭐ {match['title'][:30]}"
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"match_{match_id}"
                    )
                ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = f"⭐ <b>Мои избранные матчи ({len(favorites)})</b>"
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении избранных: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

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
            
            for channel_name, channel_url in list(links.items())[:5]:  # Показываем первые 5
                if channel_url.startswith('acestream://'):
                    channels_info += f"🎬 {channel_name}\n"
                else:
                    channels_info += f"🌐 {channel_name}\n"
            
            if len(links) > 5:
                channels_info += f"\n<i>и еще {len(links) - 5} каналов...</i>"
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при получении ссылок: {e}")
            channels_info = "\n\n⚠️ Информация о каналах недоступна"
        
        text = (
            f"<b>⚽ {match['title']}</b>\n"
            f"🔗 <a href='{match['url']}'>Оригинальная страница</a>"
            f"{channels_info}\n\n"
            f"<i>Нажмите кнопку ниже для просмотра в приложении</i>"
        )
        
        # Проверяем, в избранном ли матч
        user_id = query.from_user.id
        favorites = cache.get_favorites(user_id)
        is_favorite = match_idx in favorites
        
        favorite_button_text = "❌ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное"
        favorite_callback = f"remove_favorite_{match_idx}" if is_favorite else f"add_favorite_{match_idx}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [web_app_button],
            [InlineKeyboardButton(text=favorite_button_text, callback_data=favorite_callback)],
            [InlineKeyboardButton(text="🔔 Напоминание", callback_data=f"remind_{match_idx}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="list_matches")],
        ])
        
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выборе матча: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("add_favorite_"))
async def add_favorite(query: types.CallbackQuery):
    """Добавить матч в избранное"""
    try:
        match_id = int(query.data.split("_")[2])
        user_id = query.from_user.id
        
        cache.add_favorite(user_id, match_id)
        await query.answer("⭐ Матч добавлен в избранное!", show_alert=False)
        
        # Обновляем кнопку
        await select_match(query, FSMContext(storage=None, key=None))
        
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении в избранное: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("remove_favorite_"))
async def remove_favorite(query: types.CallbackQuery):
    """Удалить матч из избранного"""
    try:
        match_id = int(query.data.split("_")[2])
        user_id = query.from_user.id
        
        cache.remove_favorite(user_id, match_id)
        await query.answer("🗑️ Матч удален из избранного!", show_alert=False)
        
        # Обновляем кнопку
        await select_match(query, FSMContext(storage=None, key=None))
        
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении из избранного: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("remind_"))
async def set_reminder(query: types.CallbackQuery):
    """Установить напоминание о матче"""
    try:
        match_id = int(query.data.split("_")[1])
        user_id = query.from_user.id
        
        matches = await get_cached_matches()
        if match_id >= len(matches):
            await query.answer("❌ Матч не найден", show_alert=True)
            return
        
        match = matches[match_id]
        
        # Примерное время матча (сейчас + 1 час)
        match_start_time = int(time.time()) + 3600
        
        # Добавляем напоминание
        notification_service.add_match_reminder(
            user_id=user_id,
            match_id=match_id,
            match_title=match['title'],
            match_start_time=match_start_time
        )
        
        notify_time = datetime.fromtimestamp(match_start_time - 900)
        await query.answer(
            f"✅ Напоминание установлено на {notify_time.strftime('%H:%M')}",
            show_alert=False
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при установке напоминания: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@dp.callback_query(F.data == "refresh_matches")
async def refresh_matches(query: types.CallbackQuery):
    """Обновить кэш матчей"""
    cache.delete_matches()
    await query.answer("🔄 Кэш очищен, загружаю свежие матчи...", show_alert=False)
    await list_matches(query, FSMContext(storage=None, key=None))

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(query: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    await start_command(query.message, state)

@dp.message()
async def handle_message(message: types.Message):
    """Обработка остальных сообщений"""
    await message.answer(
        "Используйте команду /start для начала работы",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать", callback_data="list_matches")],
        ])
    )

async def notification_loop():
    """Фоновый цикл для отправки уведомлений"""
    notification_service.set_notification_callback(send_notification)
    notification_service.check_interval = 30  # Проверяем каждые 30 секунд
    await notification_service.start()

async def main():
    """Запуск бота"""
    logger.info("=" * 50)
    logger.info("🤖 FutLive Bot запущен")
    logger.info("=" * 50)
    logger.info(f"📦 Redis кэш: {'✅ Подключен' if cache.is_connected() else '⚠️ Локальный кэш'}")
    logger.info("🔔 Сервис уведомлений: ✅ Активен")
    logger.info("=" * 50)
    
    # Запускаем сервис уведомлений в отдельной задаче
    notification_task = asyncio.create_task(notification_loop())
    
    try:
        # Запускаем бота
        await dp.start_polling(bot)
    finally:
        notification_task.cancel()
        try:
            await notification_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
