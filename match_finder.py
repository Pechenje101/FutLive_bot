"""
Match Finder - парсер матчей с livetv.sx
Извлекает embed URL для iframe
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
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
            self._initialized = True
            logger.info("✅ Браузер инициализирован")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
    
    async def close_browser(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self._playwright: await self._playwright.stop()
        except: pass
        self._initialized = False
    
    async def find_live_matches(self) -> List[Dict]:
        matches = []
        try:
            if not await self._init_browser(): return []
            
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
                    mid = hashlib.md5(m['href'].encode()).hexdigest()[:10]
                    if mid in seen_ids: continue
                    seen_ids.add(mid)
                    
                    matches.append({
                        'id': mid,
                        'title': self._clean_title(m['text']),
                        'sport': self._detect_sport(m['text']),
                        'time': self._extract_time(m['text']),
                        'status': '🔴 LIVE' if m['isLive'] else '⏱️ UPCOMING',
                        'league': self._extract_league(m['text']),
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
        if any(w in t for w in ['hockey', 'nhl', 'khl']): return 'hockey'
        if any(w in t for w in ['tennis', 'atp', 'wta']): return 'tennis'
        if any(w in t for w in ['basketball', 'nba']): return 'basketball'
        if 'volleyball' in t: return 'volleyball'
        if 'handball' in t: return 'handball'
        return 'football'
    
    def _extract_time(self, text: str) -> str:
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        return f"{m.group(1)}:{m.group(2)}" if m else "⏱️"
    
    def _extract_league(self, text: str) -> str:
        m = re.search(r'\(([^)]+)\)', text)
        return m.group(1)[:30] if m else ""
    
    async def get_match_data(self, match_url: str) -> Dict:
        """Извлечение embed URL для iframe"""
        result = {'embed_url': None, 'acestreams': []}
        
        try:
            logger.info(f"🎥 {match_url}")
            if not await self._init_browser(): return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Ищем webplayer iframe URL
            data = await self.page.evaluate("""
            () => {
                const result = { webplayer: null, acestreams: [] };
                
                // 1. Ссылка на webplayer.php?t=ifr
                document.querySelectorAll('a').forEach(a => {
                    const href = a.href || '';
                    if (href.includes('webplayer.php') && href.includes('t=ifr')) {
                        if (!result.webplayer) result.webplayer = href;
                    }
                });
                
                // Ace Stream
                const html = document.body.innerHTML;
                const ace = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (ace) result.acestreams = ace;
                
                return result;
            }
            """)
            
            webplayer = data.get('webplayer')
            result['acestreams'] = data.get('acestreams', [])
            
            logger.info(f"📊 Webplayer: {webplayer[:50] if webplayer else 'нет'}")
            
            # Загружаем webplayer и находим embed iframe
            if webplayer:
                embed_url = await self._get_embed_from_webplayer(webplayer)
                if embed_url:
                    result['embed_url'] = embed_url
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
        
        return result
    
    async def _get_embed_from_webplayer(self, webplayer_url: str) -> Optional[str]:
        """Получение embed URL из webplayer"""
        try:
            logger.info(f"🎬 Webplayer: {webplayer_url[:60]}...")
            
            page = await self.context.new_page()
            
            try:
                await page.goto(webplayer_url, wait_until="load", timeout=15000)
                await asyncio.sleep(3)
                
                # Ищем iframe с плеером
                embed_url = await page.evaluate("""
                () => {
                    const iframes = document.querySelectorAll('iframe');
                    for (const iframe of iframes) {
                        const src = iframe.src || '';
                        // Ищем реальный плеер (не рекламу)
                        if (src && !src.includes('ads') && !src.includes('banner') && !src.includes('cache/links')) {
                            if (src.includes('daddylive') || src.includes('player') || src.includes('stream')) {
                                return src;
                            }
                        }
                    }
                    return null;
                }
                """)
                
                await page.close()
                
                if embed_url:
                    logger.info(f"✅ Embed: {embed_url[:60]}...")
                    return embed_url
                
            except Exception as e:
                logger.warning(f"Ошибка: {e}")
                await page.close()
                
        except Exception as e:
            logger.warning(f"Ошибка webplayer: {e}")
        
        return None
