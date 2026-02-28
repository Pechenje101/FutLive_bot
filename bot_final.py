"""
FutLive Bot - Telegram бот для просмотра матчей и трансляций
Оптимизированная версия
"""

import asyncio
import logging
import signal
import sys
import re
import urllib.parse
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import os

from match_finder import MatchFinder, SPORTS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

# URL для Web App (Vercel)
WEB_APP_URL = "https://my-project-three-omega-40.vercel.app"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
finder = MatchFinder()

# Кэш с меткой времени
cache = {
    "matches": [], 
    "by_sport": {}, 
    "ready": False, 
    "last_update": 0,
    "update_interval": 60,  # Обновление каждую минуту
}

# Языки для Ace Stream
LANGUAGE_MARKERS = [
    {'flag': '🇷🇺', 'name': 'Русский'},
    {'flag': '🇬🇧', 'name': 'English'},
    {'flag': '🇩🇪', 'name': 'Deutsch'},
    {'flag': '🇪🇸', 'name': 'Español'},
    {'flag': '🇮🇹', 'name': 'Italiano'},
    {'flag': '🇫🇷', 'name': 'Français'},
    {'flag': '🇵🇹', 'name': 'Português'},
    {'flag': '🌍', 'name': 'Other'},
]


class SubscribeStates(StatesGroup):
    waiting_for_team = State()
    waiting_for_search = State()


def normalize_team_name(name: str) -> str:
    return re.sub(r'[^\w\s]', '', name.lower().strip())


def find_team_matches(team_name: str, matches: list) -> list:
    team_normalized = normalize_team_name(team_name)
    result = []
    for m in matches:
        title_normalized = normalize_team_name(m['title'])
        if team_normalized in title_normalized:
            result.append(m)
    return result


def get_web_app_url(match: dict, auto_play: bool = False) -> str:
    """Генерирует URL для Web App плеера"""
    params = {
        'title': match['title'],
        'time': match['time'],
        'status': match['status'],
        'league': match.get('league', ''),
        'url': match['url'],
    }
    
    # Ace streams as JSON
    if match.get('acestreams'):
        params['acestreams'] = urllib.parse.quote(json.dumps(match['acestreams']))
    
    return WEB_APP_URL + '?' + urllib.parse.urlencode(params)


def format_acestream_sources(acestreams: list) -> str:
    """Форматирует список Ace Stream ссылок"""
    if not acestreams:
        return ""
    
    result = f"\n\n<b>📺 Ace Stream ({len(acestreams)} источников):</b>\n"
    
    for i, link in enumerate(acestreams[:6]):
        lang_info = LANGUAGE_MARKERS[i] if i < len(LANGUAGE_MARKERS) else LANGUAGE_MARKERS[-1]
        result += f"{i+1}. {lang_info['flag']} {lang_info['name']}\n   <code>{link}</code>\n"
    
    if len(acestreams) > 6:
        result += f"\n<i>... и еще {len(acestreams) - 6} источников</i>"
    
    return result


def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 LIVE сейчас", callback_data="live")],
        [InlineKeyboardButton(text="📋 Все матчи", callback_data="all")],
        [InlineKeyboardButton(text="🔍 Поиск матча", callback_data="search")],
        [InlineKeyboardButton(text="🏆 По спорту", callback_data="sports")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ])


async def refresh_cache():
    """Обновляет кэш матчей"""
    global cache
    
    while True:
        try:
            now = datetime.now().timestamp()
            
            # Check if update needed
            if now - cache["last_update"] < cache["update_interval"]:
                await asyncio.sleep(5)
                continue
            
            logger.info("🔄 Обновление кэша...")
            
            matches = await finder.find_live_matches()
            
            if matches:
                # Remove duplicates by id
                seen = set()
                unique = []
                for m in matches:
                    if m["id"] not in seen:
                        seen.add(m["id"])
                        unique.append(m)
                
                # Group by sport
                by_sport = {}
                for m in unique:
                    by_sport.setdefault(m['sport'], []).append(m)
                
                cache = {
                    "matches": unique,
                    "by_sport": by_sport,
                    "ready": True,
                    "last_update": now,
                    "update_interval": cache["update_interval"],
                }
                
                live_count = sum(1 for m in unique if "LIVE" in m["status"])
                logger.info(f"✅ Кэш: {len(unique)} матчей, {live_count} LIVE")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кэша: {e}")
        
        await asyncio.sleep(30)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    live_count = sum(1 for m in cache["matches"] if "LIVE" in m["status"])
    
    text = f"🏆 <b>FutLive Bot</b>\n\n"
    text += f"📊 Матчей: {len(cache['matches'])}\n"
    text += f"🔴 LIVE: {live_count}\n\n"
    text += "👇 <b>Выберите:</b>"
    
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")


@dp.callback_query(F.data == "menu")
async def go_menu(cb: types.CallbackQuery):
    await cb.message.edit_text("🏆 <b>FutLive Bot</b>\n\n👇 <b>Выберите:</b>", reply_markup=get_main_menu(), parse_mode="HTML")
    await cb.answer()


# ============ ПОИСК ============

@dp.callback_query(F.data == "search")
async def search_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "🔍 <b>Поиск матчей</b>\n\n"
        "Введите название команды:\n"
        "(например: Эспаньол, Барселона)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="menu")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(SubscribeStates.waiting_for_search)
    await cb.answer()


@dp.message(SubscribeStates.waiting_for_search)
async def process_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("❌ Минимум 2 символа.")
        return
    
    matches = find_team_matches(query, cache["matches"])
    
    if not matches:
        await message.answer(f"😔 Матчи с «{query}» не найдены.", reply_markup=get_main_menu())
        await state.clear()
        return
    
    live = [m for m in matches if "LIVE" in m["status"]]
    
    text = f"🔍 <b>Результаты: «{query}»</b>\n\nНайдено: {len(matches)} матчей\n🔴 LIVE: {len(live)}"
    
    btns = []
    for m in matches[:8]:
        prefix = "🔴" if "LIVE" in m["status"] else f"⏱️{m['time']}"
        btns.append([InlineKeyboardButton(text=f"{prefix} {m['title'][:35]}", callback_data=f"m_{m['id']}")])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await state.clear()


# ============ ПРОСМОТР МАТЧЕЙ ============

@dp.callback_query(F.data == "live")
async def show_live(cb: types.CallbackQuery):
    matches = [m for m in cache["matches"] if "LIVE" in m["status"]]
    
    if not matches:
        await cb.answer("Нет LIVE трансляций сейчас", show_alert=True)
        return
    
    text = f"🔴 <b>LIVE трансляции</b> ({len(matches)})"
    
    btns = []
    for m in matches[:10]:
        btns.append([InlineKeyboardButton(text=f"🔴 {m['title'][:38]}", callback_data=f"m_{m['id']}")])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data == "all")
async def show_all(cb: types.CallbackQuery):
    matches = cache["matches"]
    
    if not matches:
        await cb.answer("Загрузка матчей...", show_alert=True)
        return
    
    live = [m for m in matches if "LIVE" in m["status"]]
    upcoming = [m for m in matches if "LIVE" not in m["status"]]
    
    text = f"📋 <b>Все матчи</b> ({len(matches)})\n🔴 LIVE: {len(live)}"
    
    btns = []
    
    # Show LIVE first
    for m in live[:5]:
        btns.append([InlineKeyboardButton(text=f"🔴 {m['title'][:38]}", callback_data=f"m_{m['id']}")])
    
    # Then upcoming
    for m in upcoming[:5]:
        btns.append([InlineKeyboardButton(text=f"⏱️ {m['time']} {m['title'][:30]}", callback_data=f"m_{m['id']}")])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data == "sports")
async def show_sports(cb: types.CallbackQuery):
    by_sport = cache["by_sport"]
    
    if not by_sport:
        await cb.answer("Загрузка...", show_alert=True)
        return
    
    btns = []
    for sk, matches in sorted(by_sport.items(), key=lambda x: -len(x[1])):
        info = SPORTS.get(sk, {})
        e = info.get('emoji', '⚽')
        n = info.get('name', sk)
        live_count = sum(1 for m in matches if "LIVE" in m["status"])
        btns.append([InlineKeyboardButton(text=f"{e} {n} ({len(matches)}) 🔴{live_count}", callback_data=f"s_{sk}")])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await cb.message.edit_text(f"🏆 <b>Выберите спорт</b> ({len(cache['matches'])} матчей)", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data.startswith("s_"))
async def show_sport(cb: types.CallbackQuery):
    sport = cb.data[2:]
    matches = cache["by_sport"].get(sport, [])
    info = SPORTS.get(sport, {})
    
    if not matches:
        await cb.answer("Нет матчей", show_alert=True)
        return
    
    live = [m for m in matches if "LIVE" in m["status"]]
    other = [m for m in matches if "LIVE" not in m["status"]]
    
    text = f"{info.get('emoji','⚽')} <b>{info.get('name', sport)}</b>\n🔴 LIVE: {len(live)}"
    
    btns = []
    for m in live[:5] + other[:5]:
        prefix = "🔴" if "LIVE" in m["status"] else f"⏱️{m['time']}"
        btns.append([InlineKeyboardButton(text=f"{prefix} {m['title'][:35]}", callback_data=f"m_{m['id']}")])
    btns.append([InlineKeyboardButton(text="⬅️", callback_data="sports")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data.startswith("m_"))
async def show_match(cb: types.CallbackQuery):
    mid = cb.data[2:]
    match = next((m for m in cache["matches"] if m["id"] == mid), None)
    
    if not match:
        await cb.answer("Матч не найден", show_alert=True)
        return
    
    # Загружаем acestreams если ещё не загружены
    if not match.get('acestreams'):
        await cb.answer("⏳ Загрузка источников...", show_alert=False)
        
        try:
            match_data = await finder.get_match_data(match['url'])
            if match_data and match_data.get('acestreams'):
                match['acestreams'] = match_data['acestreams']
                
                # Обновляем в кэше
                for m in cache["matches"]:
                    if m["id"] == mid:
                        m['acestreams'] = match_data['acestreams']
                        break
                
                logger.info(f"✅ Ace Streams для {match['title'][:30]}: {len(match['acestreams'])}")
        except Exception as e:
            logger.error(f"Ошибка загрузки данных матча: {e}")
    
    web_app_url = get_web_app_url(match)
    
    text = f"📺 <b>{match['title']}</b>\n\n"
    text += f"{match['status']} {match['time']}\n"
    
    if match.get('league'):
        text += f"🏆 {match['league']}\n"
    
    btns = [
        [InlineKeyboardButton(text="📺 Смотреть в Mini App", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="🌐 Открыть на LiveTV", url=match['url'])],
    ]
    
    # Показываем Ace Stream источники
    acestreams = match.get('acestreams', [])
    if acestreams:
        text += format_acestream_sources(acestreams)
        text += "\n<i>↩️ Нажмите на ссылку чтобы скопировать</i>"
    
    text += "\n\n💡 <i>Откройте Mini App для просмотра трансляции</i>"
    
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML", disable_web_page_preview=True)


@dp.callback_query(F.data == "back")
async def go_back(cb: types.CallbackQuery):
    await show_all(cb)


@dp.callback_query(F.data == "help")
async def show_help(cb: types.CallbackQuery):
    text = (
        "ℹ️ <b>Как смотреть трансляции</b>\n\n"
        "<b>🌐 Открыть на LiveTV:</b>\n"
        "Откроет официальный сайт с плеером\n\n"
        "<b>📺 Красивый плеер:</b>\n"
        "Web App плеер внутри Telegram\n"
        "Требует установленный Ace Player\n\n"
        "<b>📺 Ace Stream ссылки:</b>\n"
        "Нажмите на ссылку → скопируйте\n"
        "Вставьте в Ace Player\n\n"
        "📥 <b>Ace Player:</b> acestream.org\n"
        "📡 <b>Источник:</b> livetv.sx"
    )
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")]
    ]), parse_mode="HTML")
    await cb.answer()


async def on_shutdown():
    logger.info("🛑 Бот остановлен")
    await finder.close_browser()
    await bot.session.close()


async def main():
    logger.info("🚀 FutLive Bot запущен!")
    
    # Запускаем обновление кэша
    asyncio.create_task(refresh_cache())
    
    # Начальная загрузка
    logger.info("📥 Загрузка матчей...")
    matches = await finder.find_live_matches()
    
    if matches:
        seen = set()
        unique = []
        for m in matches:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)
        
        by_sport = {}
        for m in unique:
            by_sport.setdefault(m['sport'], []).append(m)
        
        cache["matches"] = unique
        cache["by_sport"] = by_sport
        cache["ready"] = True
        cache["last_update"] = datetime.now().timestamp()
        
        logger.info(f"✅ Загружено: {len(unique)} матчей")
    
    signal.signal(signal.SIGTERM, lambda s, f: (asyncio.run(on_shutdown()), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda s, f: (asyncio.run(on_shutdown()), sys.exit(0)))
    
    try:
        await dp.start_polling(bot, handle_signals=False)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
