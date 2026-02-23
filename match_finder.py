"""
Match Finder - оптимизированный парсер матчей с livetv.sx
"""

import asyncio
import logging
import re
import hashlib
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SPORTS = {
    'football': {'name': 'Футбол', 'emoji': '⚽'},
    'hockey': {'name': 'Хоккей', 'emoji': '🏒'},
    'tennis': {'name': 'Теннис', 'emoji': '🎾'},
    'basketball': {'name': 'Баскетбол', 'emoji': '🏀'},
    'handball': {'name': 'Гандбол', 'emoji': '🤝'},
    'volleyball': {'name': 'Волейбол', 'emoji': '🏐'},
    'futsal': {'name': 'Мини-футбол', 'emoji': '⚽'},
}


class MatchFinder:
    """Оптимизированный парсер матчей"""
    
    def __init__(self):
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._initialized = False
        self._last_request_time = 0
    
    async def _init_browser(self):
        """Быстрая инициализация браузера"""
        if self._initialized and self.page:
            return True
            
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-images',  # Faster loading
                    '--disable-css',     # Faster loading
                ]
            )
            
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720},
            )
            self.page = await self.context.new_page()
            
            # Block unnecessary resources
            await self.page.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}', lambda route: route.abort())
            
            self._initialized = True
            logger.info("✅ Браузер инициализирован")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    async def _close_browser_internal(self):
        """Закрытие браузера"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
        except:
            pass
        finally:
            self._initialized = False
            self.page = None
            self.context = None
            self.browser = None
            self._playwright = None
    
    async def close_browser(self):
        await self._close_browser_internal()
        logger.info("✅ Браузер закрыт")
    
    async def find_live_matches(self) -> List[Dict]:
        """Быстрый парсинг матчей"""
        matches = []
        
        try:
            if not await self._init_browser():
                return []
            
            logger.info("🔍 Загрузка матчей...")
            
            # Load page with shorter timeout
            await self.page.goto(
                "https://livetv.sx/allupcoming/",
                wait_until="domcontentloaded",
                timeout=20000
            )
            
            # Wait minimal time for JS to render
            await asyncio.sleep(1)
            
            # Extract matches via JavaScript (faster than parsing HTML)
            matches_data = await self.page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();
                
                // Find all match links
                document.querySelectorAll('a[href*="eventinfo"]').forEach(link => {
                    const text = link.textContent.trim();
                    const href = link.href;
                    
                    if (!text || !href || seen.has(href)) return;
                    if (!text.includes('–') && !text.includes('-')) return;
                    
                    seen.add(href);
                    
                    // Check if LIVE
                    const parent = link.closest('tr') || link.parentElement;
                    const isLive = parent && (
                        parent.className.includes('live') || 
                        parent.innerHTML.includes('live.gif') ||
                        parent.innerHTML.includes('🔴')
                    );
                    
                    results.push({
                        text: text,
                        href: href,
                        isLive: isLive
                    });
                });
                
                return results;
            }
            """)
            
            logger.info(f"📊 Найдено сырых матчей: {len(matches_data)}")
            
            # Process matches and remove duplicates
            seen_ids = set()
            for m in matches_data:
                try:
                    # Generate unique ID
                    match_id = hashlib.md5(m['href'].encode()).hexdigest()[:10]
                    
                    if match_id in seen_ids:
                        continue
                    seen_ids.add(match_id)
                    
                    # Parse match info
                    title = m['text']
                    
                    match = {
                        'id': match_id,
                        'title': self._clean_title(title),
                        'sport': self._detect_sport(title),
                        'time': self._extract_time(title),
                        'status': '🔴 LIVE' if m['isLive'] else '⏱️ UPCOMING',
                        'league': self._extract_league(title),
                        'url': m['href'],
                        'acestreams': [],
                    }
                    
                    matches.append(match)
                    
                except Exception as e:
                    logger.warning(f"Ошибка парсинга матча: {e}")
                    continue
            
            # Sort: LIVE first, then by time
            matches.sort(key=lambda x: (0 if 'LIVE' in x['status'] else 1, x['time']))
            
            logger.info(f"✅ Обработано матчей: {len(matches)} (LIVE: {sum(1 for m in matches if 'LIVE' in m['status'])})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            import traceback
            traceback.print_exc()
        
        return matches
    
    def _clean_title(self, title: str) -> str:
        """Очистка названия матча"""
        # Remove extra spaces
        title = ' '.join(title.split())
        # Remove time prefix like "12:30 "
        title = re.sub(r'^\d{1,2}:\d{2}\s*', '', title)
        return title.strip()
    
    def _detect_sport(self, title: str) -> str:
        """Определение вида спорта"""
        t = title.lower()
        
        if any(w in t for w in ['hockey', 'хоккей', 'nhl', 'khl']):
            return 'hockey'
        if any(w in t for w in ['tennis', 'теннис', 'atp', 'wta']):
            return 'tennis'
        if any(w in t for w in ['basketball', 'баскетбол', 'nba']):
            return 'basketball'
        if any(w in t for w in ['volleyball', 'волейбол']):
            return 'volleyball'
        if any(w in t for w in ['handball', 'гандбол']):
            return 'handball'
        
        return 'football'
    
    def _extract_time(self, text: str) -> str:
        """Извлечение времени"""
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        return f"{m.group(1)}:{m.group(2)}" if m else "⏱️"
    
    def _extract_league(self, text: str) -> str:
        """Извлечение лиги"""
        # Look for text in parentheses
        m = re.search(r'\(([^)]+)\)', text)
        if m:
            return m.group(1)[:30]
        
        # Known leagues
        leagues = {
            'champions': 'ЛЧ', 'europa': 'ЛЕ', 'premier': 'EPL',
            'la liga': 'La Liga', 'serie a': 'Serie A', 
            'bundesliga': 'Bundes', 'ligue 1': 'Ligue 1',
            'nhl': 'NHL', 'nba': 'NBA', 'atp': 'ATP', 'wta': 'WTA',
        }
        
        t = text.lower()
        for k, v in leagues.items():
            if k in t:
                return v
        
        return ""
    
    async def get_match_acestreams(self, match_url: str) -> List[str]:
        """Извлечение Ace Stream ссылок"""
        acestreams = []
        
        try:
            logger.info(f"🎥 Поиск Ace Stream: {match_url}")
            
            if not await self._init_browser():
                return []
            
            # Load match page
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            
            # Wait for dynamic content
            await asyncio.sleep(2)
            
            # Try to click on video links to load player
            try:
                # Click on first video link
                await self.page.click('a[href*="ltvplayer"], a[href*="video"]').catch(lambda: None)
                await asyncio.sleep(2)
            except:
                pass
            
            # Extract page content
            content = await self.page.content()
            
            # Multiple patterns for acestream IDs
            patterns = [
                r'acestream://([a-f0-9]{40})',
                r'"id"\s*:\s*"([a-f0-9]{40})"',
                r'"contentid"\s*:\s*"([a-f0-9]{40})"',
                r'data-id=["\']([a-f0-9]{40})["\']',
                r'([a-f0-9]{40})',
            ]
            
            found_ids = set()
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for m in matches:
                    if len(m) == 40 and re.match(r'^[a-f0-9]+$', m, re.IGNORECASE):
                        found_ids.add(m.lower())
            
            # Also try JavaScript extraction
            try:
                js_ids = await self.page.evaluate("""
                () => {
                    const ids = [];
                    const html = document.body.innerHTML;
                    
                    // Find all 40-char hex strings
                    const matches = html.match(/[a-f0-9]{40}/gi) || [];
                    matches.forEach(m => ids.push(m.toLowerCase()));
                    
                    // Check data attributes
                    document.querySelectorAll('[data-id], [data-contentid], [data-acestream]').forEach(el => {
                        const id = el.dataset.id || el.dataset.contentid || el.dataset.acestream;
                        if (id && id.length === 40) ids.push(id.toLowerCase());
                    });
                    
                    return [...new Set(ids)];
                }
                """)
                
                if js_ids:
                    found_ids.update(js_ids)
            except:
                pass
            
            # Convert to acestream URLs
            for ace_id in found_ids:
                acestreams.append(f"acestream://{ace_id}")
            
            logger.info(f"✅ Найдено Ace Stream: {len(acestreams)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска Ace Stream: {e}")
        
        return acestreams
