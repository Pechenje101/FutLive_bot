"""
Match Finder - парсер матчей с livetv.sx
Извлекает HLS ссылки для видеоплеера
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
        """Извлечение HLS ссылки из матча"""
        result = {'hls_url': None, 'acestreams': []}
        
        try:
            logger.info(f"🎥 Загрузка: {match_url}")
            if not await self._init_browser(): return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Ищем webplayer URL и Ace Stream
            data = await self.page.evaluate("""
            () => {
                const result = { webplayers: [], acestreams: [] };
                
                // 1. Ссылки с webplayer.php (основной источник)
                document.querySelectorAll('a[href*="webplayer.php"]').forEach(a => {
                    const href = a.href || '';
                    if (href.includes('t=ifr') || href.includes('webplayer.php?t')) {
                        result.webplayers.push(href);
                    }
                });
                
                // 2. Ссылки с webplayer2.php
                document.querySelectorAll('a[href*="webplayer2.php"]').forEach(a => {
                    result.webplayers.push(a.href);
                });
                
                // 3. onclick с show_webplayer
                document.querySelectorAll('[onclick*="show_webplayer"]').forEach(el => {
                    const href = el.href || '';
                    if (href) result.webplayers.push(href);
                });
                
                // Ace Stream
                const html = document.body.innerHTML;
                const ace = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (ace) result.acestreams = ace;
                
                return result;
            }
            """)
            
            webplayers = list(set(data.get('webplayers', [])))
            result['acestreams'] = data.get('acestreams', [])
            
            logger.info(f"📊 Webplayers: {len(webplayers)}, Ace: {len(result['acestreams'])}")
            
            # Извлекаем HLS из webplayer
            if webplayers:
                # Приоритет webplayer.php?t=ifr
                iframe_player = next((w for w in webplayers if 'webplayer.php' in w and 't=ifr' in w), None)
                wp_url = iframe_player or webplayers[0]
                
                hls = await self._extract_hls(wp_url)
                if hls:
                    result['hls_url'] = hls
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
        
        return result
    
    async def _extract_hls(self, webplayer_url: str) -> Optional[str]:
        """Извлечение HLS из webplayer"""
        try:
            logger.info(f"🎬 Webplayer: {webplayer_url[:60]}...")
            
            hls_urls = []
            page = await self.context.new_page()
            
            async def handle_response(response):
                url = response.url
                # Ищем m3u8 файлы (HLS потоки)
                if '.m3u8' in url and 'ad' not in url.lower():
                    # Приоритет для 720p и 1080p
                    if '720p' in url or '1080p' in url:
                        hls_urls.insert(0, url)
                    else:
                        hls_urls.append(url)
                    logger.info(f"  ✅ HLS: {url[:60]}...")
            
            page.on('response', handle_response)
            
            try:
                await page.goto(webplayer_url, wait_until="load", timeout=20000)
                await asyncio.sleep(4)  # Ждём загрузки видео
            except Exception as e:
                logger.warning(f"Таймаут загрузки (игнорируем): {e}")
                await asyncio.sleep(2)
            
            await page.close()
            
            if hls_urls:
                logger.info(f"✅ Найдено HLS: {len(hls_urls)}, выбираем лучший")
                return hls_urls[0]
                
        except Exception as e:
            logger.warning(f"Ошибка HLS: {e}")
        
        return None
