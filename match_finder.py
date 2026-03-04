"""
Match Finder - парсер матчей с livetv.sx
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
    def __init__(self):
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._initialized = False
    
    async def _init_browser(self):
        if self._initialized and self.page:
            return True
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = await self.context.new_page()
            self._initialized = True
            logger.info("✅ Браузер инициализирован")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    async def close_browser(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self._playwright: await self._playwright.stop()
        except: pass
        self._initialized = False
        self.page = self.context = self.browser = self._playwright = None
    
    async def find_live_matches(self) -> List[Dict]:
        matches = []
        try:
            if not await self._init_browser(): return []
            
            logger.info("🔍 Загрузка матчей...")
            await self.page.goto("https://livetv.sx/allupcoming/", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)
            
            matches_data = await self.page.evaluate("""
            () => {
                const results = [], seen = new Set();
                document.querySelectorAll('a[href*="eventinfo"]').forEach(link => {
                    const text = link.textContent.trim(), href = link.href;
                    if (!text || !href || seen.has(href)) return;
                    if (!text.includes('–') && !text.includes('-')) return;
                    seen.add(href);
                    const parent = link.closest('tr') || link.parentElement;
                    const isLive = parent && (parent.className.includes('live') || parent.innerHTML.includes('live.gif'));
                    results.push({ text, href, isLive });
                });
                return results;
            }
            """)
            
            seen_ids = set()
            for m in matches_data:
                try:
                    match_id = hashlib.md5(m['href'].encode()).hexdigest()[:10]
                    if match_id in seen_ids: continue
                    seen_ids.add(match_id)
                    
                    title = m['text']
                    matches.append({
                        'id': match_id,
                        'title': self._clean_title(title),
                        'sport': self._detect_sport(title),
                        'time': self._extract_time(title),
                        'status': '🔴 LIVE' if m['isLive'] else '⏱️ UPCOMING',
                        'league': self._extract_league(title),
                        'url': m['href'],
                        'acestreams': [],
                    })
                except: continue
            
            matches.sort(key=lambda x: (0 if 'LIVE' in x['status'] else 1, x['time']))
            logger.info(f"✅ Матчей: {len(matches)}")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
        return matches
    
    def _clean_title(self, title: str) -> str:
        return re.sub(r'^\d{1,2}:\d{2}\s*', '', ' '.join(title.split())).strip()
    
    def _detect_sport(self, title: str) -> str:
        t = title.lower()
        if any(w in t for w in ['hockey', 'хоккей', 'nhl', 'khl']): return 'hockey'
        if any(w in t for w in ['tennis', 'теннис', 'atp', 'wta']): return 'tennis'
        if any(w in t for w in ['basketball', 'баскетбол', 'nba']): return 'basketball'
        if any(w in t for w in ['volleyball', 'волейбол']): return 'volleyball'
        if any(w in t for w in ['handball', 'гандбол']): return 'handball'
        return 'football'
    
    def _extract_time(self, text: str) -> str:
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        return f"{m.group(1)}:{m.group(2)}" if m else "⏱️"
    
    def _extract_league(self, text: str) -> str:
        m = re.search(r'\(([^)]+)\)', text)
        return m.group(1)[:30] if m else ""
    
    async def get_match_data(self, match_url: str) -> Dict:
        """Извлечение embed iframe URL из матча"""
        result = {
            'embed_url': None,  # URL для iframe
            'acestreams': []
        }
        
        try:
            logger.info(f"🎥 Загрузка: {match_url}")
            if not await self._init_browser(): return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Извлекаем embed URL и Ace Stream
            data = await self.page.evaluate("""
            () => {
                const result = { embed_url: null, acestreams: [] };
                
                // 1. Ищем webplayer.php?t=ifr в HTML
                const html = document.body.innerHTML;
                
                // Паттерн для embed iframe
                const embedMatch = html.match(/["'](\\/\\/cdn\\.livetv[^"']*webplayer\\.php\\?t=ifr[^"']*)["']/i);
                if (embedMatch) {
                    result.embed_url = embedMatch[1].replace(/&amp;/g, '&');
                }
                
                // 2. Ищем ссылку на webplayer
                if (!result.embed_url) {
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        const href = link.href || '';
                        if (href.includes('webplayer.php') && href.includes('t=ifr')) {
                            result.embed_url = href;
                            break;
                        }
                    }
                }
                
                // 3. Ace Stream
                const aceMatches = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (aceMatches) {
                    result.acestreams = aceMatches;
                }
                
                return result;
            }
            """)
            
            embed_url = data.get('embed_url')
            
            if embed_url:
                # Делаем URL абсолютным
                if embed_url.startswith('//'):
                    embed_url = 'https:' + embed_url
                result['embed_url'] = embed_url
                logger.info(f"✅ Embed URL: {embed_url[:60]}...")
            else:
                logger.warning("❌ Embed URL не найден")
            
            result['acestreams'] = data.get('acestreams', [])
            logger.info(f"✅ AceStreams: {len(result['acestreams'])}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
        
        return result
