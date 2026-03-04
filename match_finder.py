"""
Match Finder - парсер матчей с livetv.sx
"""

import asyncio
import logging
import re
import hashlib
from typing import Dict, List, Optional
import json

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
            'embed_url': None,
            'acestreams': [],
            'hls_url': None
        }
        
        try:
            logger.info(f"🎥 Загрузка: {match_url}")
            if not await self._init_browser(): return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Извлекаем ВСЕ возможные URL для плеера
            data = await self.page.evaluate("""
            () => {
                const result = { 
                    embed_url: null, 
                    acestreams: [],
                    webplayer_url: null,
                    iframe_src: null,
                    onclick_url: null,
                    direct_embed: null,
                    player_id: null
                };
                
                const html = document.body.innerHTML;
                
                // 1. Ищем webplayer.php?t=ifr в разных форматах
                // Формат 1: в атрибуте src или data-src
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {
                    const src = iframe.src || iframe.getAttribute('data-src') || '';
                    if (src.includes('webplayer.php') || src.includes('apl393') || src.includes('embed')) {
                        result.iframe_src = src;
                        break;
                    }
                }
                
                // Формат 2: в onclick или других атрибутах ссылок
                const links = document.querySelectorAll('a');
                for (const link of links) {
                    const onclick = link.getAttribute('onclick') || '';
                    const href = link.href || '';
                    
                    // Ищем webplayer в onclick
                    if (onclick.includes('webplayer.php') || onclick.includes('t=ifr')) {
                        const match = onclick.match(/['"]([^'"]*(?:webplayer\\.php|t=ifr)[^'"]*)['"]/);
                        if (match) {
                            result.onclick_url = match[1].replace(/\\\\/g, '');
                        }
                    }
                    
                    // Ищем webplayer в href
                    if (href.includes('webplayer.php') && href.includes('t=ifr')) {
                        result.webplayer_url = href;
                    }
                }
                
                // Формат 3: прямой поиск в HTML
                const patterns = [
                    /["']([^"']*webplayer\\.php\\?t=ifr[^"']*)["']/gi,
                    /["']([^"']*cdn\\.livetv[^"']*)["']/gi,
                    /["']([^"']*emb\\.apl393[^"']*)["']/gi,
                    /src=["']([^"']*player[^"']*)["']/gi
                ];
                
                for (const pattern of patterns) {
                    const matches = html.match(pattern);
                    if (matches && matches.length > 0) {
                        const url = matches[0].replace(/src=["']/, '').replace(/["']$/, '').replace(/&amp;/g, '&');
                        if (url && !result.direct_embed) {
                            result.direct_embed = url;
                        }
                    }
                }
                
                // 4. Ищем player ID
                const idMatch = html.match(/player[_-]?id["':=\\s]+["']?([a-zA-Z0-9]+)["']?/i);
                if (idMatch) {
                    result.player_id = idMatch[1];
                }
                
                // 5. Ищем event ID для прямого конструирования URL
                const eventMatch = html.match(/event[_-]?id["':=\\s]+["']?(\\d+)["']?/i);
                if (eventMatch) {
                    result.event_id = eventMatch[1];
                }
                
                // 6. Ищем ID в URL webplayer
                const webplayerIdMatch = html.match(/webplayer\\.php\\?[^"']*c=([^"&']+)/i);
                if (webplayerIdMatch) {
                    result.webplayer_c = webplayerIdMatch[1];
                }
                
                // Ace Stream
                const aceMatches = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (aceMatches) {
                    result.acestreams = aceMatches;
                }
                
                return result;
            }
            """)
            
            logger.info(f"📊 Найденные данные: {json.dumps({k: v for k, v in data.items() if v}, indent=2)}")
            
            # Приоритет embed URL
            embed_url = None
            
            # Приоритет 1: iframe src
            if data.get('iframe_src'):
                embed_url = data['iframe_src']
                logger.info(f"✅ Найден iframe src: {embed_url[:60]}...")
            
            # Приоритет 2: onclick URL
            if not embed_url and data.get('onclick_url'):
                embed_url = data['onclick_url']
                logger.info(f"✅ Найден onclick URL: {embed_url[:60]}...")
            
            # Приоритет 3: webplayer URL из ссылки
            if not embed_url and data.get('webplayer_url'):
                embed_url = data['webplayer_url']
                logger.info(f"✅ Найден webplayer URL: {embed_url[:60]}...")
            
            # Приоритет 4: прямой embed из HTML
            if not embed_url and data.get('direct_embed'):
                embed_url = data['direct_embed']
                logger.info(f"✅ Найден direct embed: {embed_url[:60]}...")
            
            # Делаем URL абсолютным
            if embed_url:
                if embed_url.startswith('//'):
                    embed_url = 'https:' + embed_url
                elif embed_url.startswith('/'):
                    embed_url = 'https://livetv.sx' + embed_url
                elif not embed_url.startswith('http'):
                    embed_url = 'https://' + embed_url
                
                result['embed_url'] = embed_url
                logger.info(f"✅ Итоговый embed URL: {embed_url}")
            else:
                logger.warning("❌ Embed URL не найден, пробуем конструировать...")
                
                # Если есть webplayer_c, конструируем URL
                if data.get('webplayer_c'):
                    result['embed_url'] = f"https://cdn.livetvcdn.net/webplayer.php?t=ifr&c={data['webplayer_c']}"
                    logger.info(f"🔧 Сконструирован URL: {result['embed_url']}")
            
            result['acestreams'] = data.get('acestreams', [])
            
            # Если Ace Streams найдены, логируем
            if result['acestreams']:
                logger.info(f"✅ AceStreams: {len(result['acestreams'])}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return result
