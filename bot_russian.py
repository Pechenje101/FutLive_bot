"""
FutLive Bot - Telegram бот с русскоязычными источниками
"""

import asyncio
import logging
import signal
import sys
import re
import urllib.parse
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import os

# Импорт русскоязычных источников
from russian_sources import MultiRussianParser, SPORTS_RU, get_sports_emoji, get_sports_name

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

WEB_APP_URL = "https://my-project-three-omega-40.vercel.app"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
parser = MultiRussianParser()

# Кэш
cache = {
    "matches": [],
    "by_sport": {},
    "ready": False,
    "last_update": 0,
    "update_interval": 60,
}

# Источники для отображения
SOURCES_INFO = {
    'LiveTV': {'emoji': '🔴', 'desc': 'Трансляции матчей'},
    'Torrent-TV': {'emoji': '🚀', 'desc': 'ТВ каналы (Ace Stream)'},
    'Sport-TV': {'emoji': '📺', 'desc': 'Спортивные каналы'},
    'ArenaVision': {'emoji': '🎯', 'desc': 'Ace Stream матчи'},
}


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


def get_web_app_url(match: dict) -> str:
    """Генерирует URL для Web App плеера"""
    params = {
        'title': match['title'],
        'time': match.get('time', ''),
        'status': match.get('status', ''),
        'url': match['url'],
    }
    
    if match.get('embed_url'):
        params['embed_url'] = match['embed_url']
    
    if match.get('acestreams'):
        params['acestreams'] = urllib.parse.quote(json.dumps(match['acestreams']))
    
    return WEB_APP_URL + '?' + urllib.parse.urlencode(params)


def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 LIVE сейчас", callback_data="live")],
        [InlineKeyboardButton(text="📋 Все матчи", callback_data="all")],
        [InlineKeyboardButton(text="🔍 Поиск матча", callback_data="search")],
        [InlineKeyboardButton(text="🏆 По спорту", callback_data="sports")],
        [InlineKeyboardButton(text="📺 ТВ Каналы", callback_data="channels")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ])


async def refresh_cache():
    """Обновляет кэш матчей"""
    global cache
    
    while True:
        try:
            now = datetime.now().timestamp()
            
            if now - cache["last_update"] < cache["update_interval"]:
                await asyncio.sleep(5)
                continue
            
            logger.info("🔄 Обновление кэша...")
            
            matches = await parser.get_all_matches()
            
            if matches:
                # Группировка по спорту
                by_sport = {}
                for m in matches:
                    by_sport.setdefault(m['sport'], []).append(m)
                
                cache = {
                    "matches": matches,
                    "by_sport": by_sport,
                    "ready": True,
                    "last_update": now,
                    "update_interval": cache["update_interval"],
                }
                
                live_count = sum(1 for m in matches if "LIVE" in m.get("status", ""))
                logger.info(f"✅ Кэш: {len(matches)} матчей, {live_count} LIVE")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления: {e}")
        
        await asyncio.sleep(30)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    matches = cache["matches"]
    live_count = sum(1 for m in matches if "LIVE" in m.get("status", ""))
    
    text = f"🏆 <b>FutLive Bot</b>\n\n"
    text += f"📊 Матчей: {len(matches)}\n"
    text += f"🔴 LIVE: {live_count}\n\n"
    text += "📡 <b>Источники:</b>\n"
    text += "🔴 LiveTV - трансляции\n"
    text += "📺 ТВ каналы - 24/7\n\n"
    text += "👇 <b>Выберите:</b>"
    
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")


@dp.callback_query(F.data == "menu")
async def go_menu(cb: types.CallbackQuery):
    await cb.message.edit_text("🏆 <b>FutLive Bot</b>\n\n👇 Выберите:", reply_markup=get_main_menu(), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data == "live")
async def show_live(cb: types.CallbackQuery):
    matches = [m for m in cache["matches"] if "LIVE" in m.get("status", "")]
    
    if not matches:
        await cb.answer("Нет LIVE трансляций сейчас", show_alert=True)
        return
    
    text = f"🔴 <b>LIVE трансляции</b> ({len(matches)})"
    
    btns = []
    for m in matches[:10]:
        emoji = m.get('source_emoji', '🔴')
        btns.append([InlineKeyboardButton(
            text=f"{emoji} {m['title'][:38]}",
            callback_data=f"m_{m['id']}"
        )])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data == "all")
async def show_all(cb: types.CallbackQuery):
    matches = cache["matches"]
    
    if not matches:
        await cb.answer("Загрузка матчей...", show_alert=True)
        return
    
    live = [m for m in matches if "LIVE" in m.get("status", "")]
    upcoming = [m for m in matches if "LIVE" not in m.get("status", "")]
    
    text = f"📋 <b>Все матчи</b> ({len(matches)})\n🔴 LIVE: {len(live)}"
    
    btns = []
    
    for m in live[:5]:
        emoji = m.get('source_emoji', '🔴')
        btns.append([InlineKeyboardButton(text=f"{emoji} {m['title'][:38]}", callback_data=f"m_{m['id']}")])
    
    for m in upcoming[:5]:
        time_str = m.get('time', '⏱️')
        btns.append([InlineKeyboardButton(text=f"⏱️ {time_str} {m['title'][:30]}", callback_data=f"m_{m['id']}")])
    
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
    for sport, matches in sorted(by_sport.items(), key=lambda x: -len(x[1])):
        info = SPORTS_RU.get(sport, {})
        emoji = info.get('emoji', '⚽')
        name = info.get('name', sport)
        live_count = sum(1 for m in matches if "LIVE" in m.get("status", ""))
        btns.append([InlineKeyboardButton(
            text=f"{emoji} {name} ({len(matches)}) 🔴{live_count}",
            callback_data=f"s_{sport}"
        )])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await cb.message.edit_text(
        f"🏆 <b>Выберите спорт</b> ({len(cache['matches'])} матчей)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        parse_mode="HTML"
    )
    await cb.answer()


@dp.callback_query(F.data == "channels")
async def show_channels(cb: types.CallbackQuery):
    """Показать ТВ каналы"""
    matches = [m for m in cache["matches"] if m.get('source') in ['Sport-TV', 'Torrent-TV']]
    
    text = "📺 <b>ТВ Каналы 24/7</b>\n\n"
    text += "Евроспорт, Матч ТВ, Футбол и др.\n"
    text += "Качество: HD\n\n"
    text += "Выберите канал:"
    
    btns = []
    for m in matches[:10]:
        btns.append([InlineKeyboardButton(
            text=f"📺 {m['title'].replace('📺 ', '')}",
            callback_data=f"m_{m['id']}"
        )])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cb.answer()


@dp.callback_query(F.data.startswith("s_"))
async def show_sport(cb: types.CallbackQuery):
    sport = cb.data[2:]
    matches = cache["by_sport"].get(sport, [])
    info = SPORTS_RU.get(sport, {})
    
    if not matches:
        await cb.answer("Нет матчей", show_alert=True)
        return
    
    live = [m for m in matches if "LIVE" in m.get("status", "")]
    other = [m for m in matches if "LIVE" not in m.get("status", "")]
    
    text = f"{info.get('emoji','⚽')} <b>{info.get('name', sport)}</b>\n🔴 LIVE: {len(live)}"
    
    btns = []
    for m in live[:5] + other[:5]:
        prefix = m.get('source_emoji', '🔴') if "LIVE" in m.get("status", "") else f"⏱️{m.get('time', '')}"
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
    
    # Загружаем данные плеера
    if not match.get('embed_url') and not match.get('acestreams'):
        await cb.answer("⏳ Загрузка плеера...", show_alert=False)
        
        try:
            stream_data = await parser.get_stream_url(match)
            if stream_data.get('embed_url'):
                match['embed_url'] = stream_data['embed_url']
            if stream_data.get('acestreams'):
                match['acestreams'] = stream_data['acestreams']
            
            logger.info(f"✅ {match['title'][:30]}: embed={bool(match.get('embed_url'))}, ace={len(match.get('acestreams', []))}")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
    
    source = match.get('source', 'LiveTV')
    source_info = SOURCES_INFO.get(source, {})
    
    text = f"📺 <b>{match['title']}</b>\n\n"
    text += f"{match.get('status', '')} {match.get('time', '')}\n"
    
    if match.get('league'):
        text += f"🏆 {match['league']}\n"
    
    text += f"\n📡 Источник: {source_info.get('emoji', '🔴')} {source}"
    
    if match.get('embed_url'):
        text += "\n✅ <b>Плеер готов!</b>"
    
    web_app_url = get_web_app_url(match)
    
    btns = [
        [InlineKeyboardButton(text="📺 Смотреть", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="🌐 Открыть сайт", url=match['url'])],
    ]
    
    if match.get('acestreams'):
        btns.append([InlineKeyboardButton(
            text=f"🚀 Ace Stream ({len(match['acestreams'])})",
            callback_data=f"ace_{mid}"
        )])
    
    btns.append([InlineKeyboardButton(text="⬅️", callback_data="back")])
    
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML", disable_web_page_preview=True)


@dp.callback_query(F.data.startswith("ace_"))
async def show_acestream(cb: types.CallbackQuery):
    """Показать Ace Stream ссылки"""
    mid = cb.data[4:]
    match = next((m for m in cache["matches"] if m["id"] == mid), None)
    
    if not match or not match.get('acestreams'):
        await cb.answer("Нет Ace Stream ссылок", show_alert=True)
        return
    
    text = f"🚀 <b>Ace Stream ссылки</b>\n\n"
    text += f"📺 {match['title']}\n\n"
    text += "<code>acestream://ID</code>\n\n"
    text += "Скопируйте и вставьте в Ace Player"
    
    for i, ace in enumerate(match['acestreams'][:3]):
        text += f"\n{i+1}. <code>{ace}</code>"
    
    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"m_{mid}")]
        ]),
        parse_mode="HTML"
    )
    await cb.answer()


@dp.callback_query(F.data == "back")
async def go_back(cb: types.CallbackQuery):
    await show_all(cb)


@dp.callback_query(F.data == "search")
async def search_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "🔍 <b>Поиск матчей</b>\n\n"
        "Введите название команды:\n"
        "(например: Спартак, Зенит, Барселона)",
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
    
    live = [m for m in matches if "LIVE" in m.get("status", "")]
    
    text = f"🔍 <b>Результаты: «{query}»</b>\n\nНайдено: {len(matches)} матчей\n🔴 LIVE: {len(live)}"
    
    btns = []
    for m in matches[:8]:
        prefix = m.get('source_emoji', '🔴') if "LIVE" in m.get("status", "") else f"⏱️{m.get('time', '')}"
        btns.append([InlineKeyboardButton(text=f"{prefix} {m['title'][:35]}", callback_data=f"m_{m['id']}")])
    
    btns.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await state.clear()


@dp.callback_query(F.data == "help")
async def show_help(cb: types.CallbackQuery):
    text = (
        "ℹ️ <b>Как смотреть трансляции</b>\n\n"
        
        "<b>🔴 LiveTV:</b>\n"
        "Трансляции матчей онлайн\n"
        "Встроенный плеер в Telegram\n\n"
        
        "<b>📺 ТВ Каналы:</b>\n"
        "Евроспорт, Матч ТВ, Футбол\n"
        "Работают 24/7\n\n"
        
        "<b>🚀 Ace Stream:</b>\n"
        "P2P трансляции\n"
        "Требует Ace Player\n"
        "Высокое качество HD\n\n"
        
        "📥 <b>Ace Player:</b> acestream.org\n"
        "📡 <b>Источники:</b> LiveTV, Sport-TV"
    )
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")]
    ]), parse_mode="HTML")
    await cb.answer()


async def on_shutdown():
    logger.info("🛑 Бот остановлен")
    await parser.close()
    await bot.session.close()


async def main():
    logger.info("🚀 FutLive Bot (Russian Sources) запущен!")
    
    # Запускаем обновление кэша
    asyncio.create_task(refresh_cache())
    
    # Начальная загрузка
    logger.info("📥 Загрузка матчей...")
    matches = await parser.get_all_matches()
    
    if matches:
        by_sport = {}
        for m in matches:
            by_sport.setdefault(m['sport'], []).append(m)
        
        cache["matches"] = matches
        cache["by_sport"] = by_sport
        cache["ready"] = True
        cache["last_update"] = datetime.now().timestamp()
        
        logger.info(f"✅ Загружено: {len(matches)} матчей")
    
    signal.signal(signal.SIGTERM, lambda s, f: (asyncio.run(on_shutdown()), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda s, f: (asyncio.run(on_shutdown()), sys.exit(0)))
    
    try:
        await dp.start_polling(bot, handle_signals=False)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
