"""
Match Finder - парсер матчей с livetv.sx используя Playwright
"""

import asyncio
import logging
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

# Словарь видов спорта с эмодзи
SPORTS = {
    'football': {'name': 'Футбол', 'emoji': '⚽'},
    'hockey': {'name': 'Хоккей', 'emoji': '🏒'},
    'tennis': {'name': 'Теннис', 'emoji': '🎾'},
    'basketball': {'name': 'Баскетбол', 'emoji': '🏀'},
    'handball': {'name': 'Гандбол', 'emoji': '🤝'},
    'volleyball': {'name': 'Волейбол', 'emoji': '🏐'},
    'futsal': {'name': 'Мини-футбол', 'emoji': '⚽'},
    'waterpolo': {'name': 'Водное поло', 'emoji': '🏊'},
    'badminton': {'name': 'Бадминтон', 'emoji': '🏸'},
    'cricket': {'name': 'Крикет', 'emoji': '🏏'},
    'rugby': {'name': 'Регби', 'emoji': '🏈'},
    'golf': {'name': 'Гольф', 'emoji': '⛳'},
    'boxing': {'name': 'Бокс', 'emoji': '🥊'},
    'mma': {'name': 'ММА', 'emoji': '🥋'},
    'cycling': {'name': 'Велоспорт', 'emoji': '🚴'},
    'motorsport': {'name': 'Автоспорт', 'emoji': '🏎️'},
}


class MatchFinder:
    """Парсер матчей с livetv.sx используя Playwright"""
    
    def __init__(self):
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._initialized = False
    
    async def _init_browser(self):
        """Инициализирует браузер Playwright"""
        if self._initialized and self.page:
            return True
            
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            
            # Используем chromium с опциями для серверных сред
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-web-security'
                ]
            )
            
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = await self.context.new_page()
            
            self._initialized = True
            logger.info("✅ Браузер инициализирован")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации браузера: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _retry_request(self, url: str, max_retries: int = 3):
        """Выполняет запрос с повторными попытками"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if not self.page:
                    success = await self._init_browser()
                    if not success:
                        await asyncio.sleep(2)
                        continue
                
                logger.info(f"🔍 Загрузка {url} (попытка {attempt + 1}/{max_retries})")
                
                await self.page.goto(
                    url, 
                    wait_until="domcontentloaded",  # Быстрее чем networkidle
                    timeout=30000
                )
                
                # Ждем загрузки контента
                await asyncio.sleep(2)
                
                # Проверяем что страница загрузилась
                content = await self.page.content()
                if len(content) < 100:
                    raise Exception("Страница пуста")
                
                return True
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Попытка {attempt + 1} неудачна: {e}")
                
                # Закрываем и переинициализируем браузер при ошибке
                await self._close_browser_internal()
                await asyncio.sleep(2)
        
        logger.error(f"❌ Все попытки исчерпаны: {last_error}")
        return False
    
    async def _close_browser_internal(self):
        """Внутренний метод закрытия браузера"""
        try:
            if self.page:
                try:
                    await self.page.close()
                except:
                    pass
                self.page = None
            
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass
                self.context = None
            
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
                self.browser = None
            
            if self._playwright:
                try:
                    await self._playwright.stop()
                except:
                    pass
                self._playwright = None
            
            self._initialized = False
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при закрытии браузера: {e}")
    
    async def find_live_matches(self):
        """Загружает матчи с livetv.sx"""
        try:
            # Пробуем загрузить страницу с retry
            success = await self._retry_request("https://livetv.sx/allupcoming/")
            
            if not success:
                logger.error("❌ Не удалось загрузить страницу")
                return []
            
            # Выполняем JavaScript для получения матчей
            matches_data = await self.page.evaluate("""
            () => {
                const matches = [];
                
                // Ищем все ссылки с текстом, содержащим " – "
                const links = document.querySelectorAll('a');
                links.forEach(link => {
                    if (link.textContent.includes(' – ') && link.href && link.href.includes('livetv')) {
                        matches.push({
                            text: link.textContent.trim(),
                            href: link.href,
                            className: link.className
                        });
                    }
                });
                
                return matches;
            }
            """)
            
            logger.info(f"✅ Найдено матчей на странице: {len(matches_data)}")
            
            # Парсим матчи
            matches = []
            for match_data in matches_data:
                try:
                    title = match_data['text']
                    url = match_data['href']
                    
                    if not title or not url:
                        continue
                    
                    # Определяем спорт
                    sport = self._detect_sport(title)
                    
                    # Извлекаем информацию
                    import hashlib
                    match_id = hashlib.md5(url.encode()).hexdigest()[:10] if url else str(hash(title))
                    match_info = {
                        'id': match_id,
                        'title': title,
                        'sport': sport,
                        'time': self._extract_time(title),
                        'status': self._get_status(match_data['className']),
                        'league': self._extract_league(title),
                        'url': url,
                    }
                    
                    matches.append(match_info)
                
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при парсинге матча: {e}")
                    continue
            
            logger.info(f"✅ Успешно спарсено матчей: {len(matches)}")
            return matches
        
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке матчей: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _detect_sport(self, title):
        """Определяет вид спорта по названию матча"""
        title_lower = title.lower()
        
        # Хоккей (проверяем первым, так как специфичные ключевые слова)
        if any(word in title_lower for word in ['хоккей', 'hockey', 'nhl', 'khl']):
            return 'hockey'
        
        # Теннис
        if any(word in title_lower for word in ['теннис', 'tennis', 'atp', 'wta', 'grand slam']):
            return 'tennis'
        
        # Баскетбол
        if any(word in title_lower for word in ['баскетбол', 'basketball', 'nba', 'euroleague']):
            return 'basketball'
        
        # Гандбол
        if any(word in title_lower for word in ['гандбол', 'handball']):
            return 'handball'
        
        # Волейбол
        if any(word in title_lower for word in ['волейбол', 'volleyball']):
            return 'volleyball'
        
        # Мини-футбол
        if any(word in title_lower for word in ['мини-футбол', 'futsal']):
            return 'futsal'
        
        # Футбол (по умолчанию для многих матчей)
        if any(word in title_lower for word in ['футбол', 'football', 'fc ', 'vs', 'premier', 'liga', 'serie', 'bundesliga', 'ligue', 'champions', 'cup', 'лига']):
            return 'football'
        
        # По умолчанию - футбол
        return 'football'
    
    def _extract_time(self, text):
        """Извлекает время из текста"""
        time_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            return f"{time_match.group(1)}:{time_match.group(2)}"
        return "⏱️"
    
    def _get_status(self, class_name):
        """Определяет статус матча по классу"""
        if not class_name:
            return "⏱️ UPCOMING"
        
        if 'live' in class_name.lower():
            return "🔴 LIVE"
        
        return "⏱️ UPCOMING"
    
    def _extract_league(self, text):
        """Извлекает лигу из текста"""
        # Ищем текст в скобках
        league_match = re.search(r'\(([^)]+)\)', text)
        if league_match:
            return league_match.group(1)
        
        # Если нет скобок, ищем известные лиги
        text_lower = text.lower()
        
        leagues = {
            'premier': 'Премьер-лига',
            'la liga': 'Ла Лига',
            'serie a': 'Серия А',
            'bundesliga': 'Бундеслига',
            'ligue 1': 'Лига 1',
            'champions': 'Лига Чемпионов',
            'europa': 'Лига Европы',
            'cup': 'Кубок',
            'nba': 'NBA',
            'nhl': 'NHL',
            'atp': 'ATP',
            'wta': 'WTA',
        }
        
        for keyword, league_name in leagues.items():
            if keyword in text_lower:
                return league_name
        
        return ""
    
    async def close_browser(self):
        """Закрывает браузер (публичный метод)"""
        await self._close_browser_internal()
        logger.info("✅ Браузер закрыт")
