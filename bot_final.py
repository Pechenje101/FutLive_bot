"""
FutLive Bot - Telegram бот для просмотра матчей и трансляций
Использует livetv.sx для получения информации о матчах и трансляциях
"""

import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from match_finder import MatchFinder, SPORTS
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не установлен!")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Инициализация парсера матчей
match_finder = MatchFinder()

# Класс для хранения состояния (вместо global переменных)
class BotState:
    def __init__(self):
        self.matches_cache = {}
        self.is_running = True
    
    def set_cache(self, matches_list):
        """Обновляет кэш матчей"""
        self.matches_cache = {}
        for match in matches_list:
            sport = match['sport']
            if sport not in self.matches_cache:
                self.matches_cache[sport] = []
            self.matches_cache[sport].append(match)
    
    def get_matches(self, sport):
        """Получает матчи из кэша по спорту"""
        return self.matches_cache.get(sport, [])
    
    def clear_cache(self):
        """Очищает кэш"""
        self.matches_cache = {}

# Глобальный экземпляр состояния
bot_state = BotState()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    logger.info(f"👤 Новый пользователь: {message.from_user.id}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Выбрать спорт", callback_data="select_sport")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
    ])
    
    await message.answer(
        "👋 Добро пожаловать в FutLive Bot!\n\n"
        "Здесь вы можете:\n"
        "⚽ Смотреть список матчей по видам спорта\n"
        "📺 Найти трансляции на livetv.sx\n"
        "🏆 Выбрать интересующий вид спорта\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "select_sport")
async def select_sport(callback: types.CallbackQuery):
    """Выбор спорта с показом количества матчей"""
    logger.info(f"🏆 Пользователь {callback.from_user.id} выбирает спорт")
    
    await callback.answer("⏳ Загружаю виды спорта...", show_alert=False)
    
    try:
        # Получаем все матчи
        all_matches = await match_finder.find_live_matches()
        
        if not all_matches:
            await callback.message.edit_text(
                "❌ Матчи не найдены. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
                ])
            )
            return
        
        # Сохраняем матчи в кэш через класс состояния
        bot_state.set_cache(all_matches)
        
        # Группируем матчи по спорту и считаем количество
        sports_count = {}
        for match in all_matches:
            sport = match['sport']
            if sport not in sports_count:
                sports_count[sport] = 0
            sports_count[sport] += 1
        
        # Формируем кнопки для каждого спорта
        keyboard_buttons = []
        for sport in sorted(sports_count.keys()):
            sport_info = SPORTS.get(sport, {})
            emoji = sport_info.get('emoji', '⚽')
            name = sport_info.get('name', sport)
            count = sports_count[sport]
            
            button_text = f"{emoji} {name} +{count}"
            keyboard_buttons.append([
                InlineKeyboardButton(text=button_text, callback_data=f"sport_{sport}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
        
        text = "🏆 **Выберите вид спорта:**\n\n"
        text += "Нажмите на спорт, чтобы увидеть все матчи"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке спортов: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(
            "❌ Ошибка при загрузке спортов. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ])
        )


@dp.callback_query(F.data.startswith("sport_"))
async def show_sport_matches(callback: types.CallbackQuery):
    """Показать все матчи по выбранному спорту"""
    sport = callback.data.replace("sport_", "")
    logger.info(f"🏆 Пользователь {callback.from_user.id} выбрал спорт: {sport}")
    
    await callback.answer("⏳ Загружаю матчи...", show_alert=False)
    
    try:
        # Получаем матчи из кэша
        matches = bot_state.get_matches(sport)
        
        if not matches:
            await callback.message.edit_text(
                f"❌ Матчи по спорту не найдены.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="select_sport")],
                ])
            )
            return
        
        # Формируем сообщение
        sport_info = SPORTS.get(sport, {})
        emoji = sport_info.get('emoji', '⚽')
        name = sport_info.get('name', sport)
        
        text = f"{emoji} **{name}**\n\n"
        text += f"Найдено матчей: {len(matches)}\n\n"
        text += "Нажмите на матч, чтобы открыть трансляцию на livetv.sx\n\n"
        
        # Показываем матчи с временем и лигой (лимит для Telegram)
        max_matches_to_show = min(len(matches), 20)
        for i, match in enumerate(matches[:max_matches_to_show], 1):
            text += f"{i}. {match['title']}\n"
            text += f"   {match['status']} {match['time']}\n"
            text += f"   {match['league']}\n\n"
        
        if len(matches) > max_matches_to_show:
            text += f"... и еще {len(matches) - max_matches_to_show} матчей\n"
        
        # Формируем кнопки для каждого матча (лимит 10 кнопок)
        keyboard_buttons = []
        for match in matches[:10]:
            # Сокращаем текст кнопки до 60 символов
            button_text = f"{match['status']} {match['time']} - {match['title'][:40]}"
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            keyboard_buttons.append([
                InlineKeyboardButton(text=button_text, url=match['url'])
            ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="select_sport")])
        
        # Если текст слишком длинный, обрезаем
        if len(text) > 4000:
            text = f"{emoji} **{name}**\n\n"
            text += f"Найдено матчей: {len(matches)}\n\n"
            text += "Нажмите на матч, чтобы открыть трансляцию на livetv.sx"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке матчей: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(
            "❌ Ошибка при загрузке матчей. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="select_sport")],
            ])
        )


@dp.callback_query(F.data == "about")
async def about(callback: types.CallbackQuery):
    """Информация о боте"""
    await callback.message.edit_text(
        "ℹ️ **О FutLive Bot**\n\n"
        "Это бот для просмотра матчей и трансляций.\n\n"
        "✨ **Возможности:**\n"
        "⚽ Список матчей по видам спорта\n"
        "📺 Прямые ссылки на трансляции на livetv.sx\n"
        "🔴 Информация о статусе матча (LIVE/UPCOMING)\n"
        "⏱️ Время начала матча\n"
        "🏆 Фильтрация по виду спорта\n\n"
        "🔗 **Источники:**\n"
        "- livetv.sx - трансляции матчей\n\n"
        "📧 **Контакты:**\n"
        "Для вопросов и предложений пишите разработчику.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Выбрать спорт", callback_data="select_sport")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
    ])
    
    await callback.message.edit_text(
        "👋 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


async def on_shutdown():
    """Корректное завершение работы"""
    logger.info("🛑 Завершение работы бота...")
    
    # Закрываем браузер
    await match_finder.close_browser()
    
    # Закрываем сессию бота
    await bot.session.close()
    
    logger.info("✅ Бот успешно остановлен")


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"📢 Получен сигнал {signum}, останавливаю бота...")
    bot_state.is_running = False
    # Создаем новую event loop для shutdown
    asyncio.run(on_shutdown())
    sys.exit(0)


async def main():
    """Основная функция"""
    logger.info("🚀 Запуск FutLive Bot...")
    logger.info(f"🤖 Бот запущен")
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=False  # Мы сами обрабатываем сигналы
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
