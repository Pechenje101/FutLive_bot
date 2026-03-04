"""
Match Finder - оптимизированный парсер матчей с livetv.sx
Поддержка Ace Stream, Web плееров и прямых ссылок
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
                    '--disable-images',
                    '--disable-css',
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
            
            await self.page.goto(
                "https://livetv.sx/allupcoming/",
                wait_until="domcontentloaded",
                timeout=20000
            )
            
            await asyncio.sleep(1)
            
            matches_data = await self.page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();
                
                document.querySelectorAll('a[href*="eventinfo"]').forEach(link => {
                    const text = link.textContent.trim();
                    const href = link.href;
                    
                    if (!text || !href || seen.has(href)) return;
                    if (!text.includes('–') && !text.includes('-')) return;
                    
                    seen.add(href);
                    
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
            
            seen_ids = set()
            for m in matches_data:
                try:
                    match_id = hashlib.md5(m['href'].encode()).hexdigest()[:10]
                    
                    if match_id in seen_ids:
                        continue
                    seen_ids.add(match_id)
                    
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
            
            matches.sort(key=lambda x: (0 if 'LIVE' in x['status'] else 1, x['time']))
            
            logger.info(f"✅ Обработано матчей: {len(matches)} (LIVE: {sum(1 for m in matches if 'LIVE' in m['status'])})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            import traceback
            traceback.print_exc()
        
        return matches
    
    def _clean_title(self, title: str) -> str:
        title = ' '.join(title.split())
        title = re.sub(r'^\d{1,2}:\d{2}\s*', '', title)
        return title.strip()
    
    def _detect_sport(self, title: str) -> str:
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
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        return f"{m.group(1)}:{m.group(2)}" if m else "⏱️"
    
    def _extract_league(self, text: str) -> str:
        m = re.search(r'\(([^)]+)\)', text)
        if m:
            return m.group(1)[:30]
        
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
    
    async def get_match_data(self, match_url: str) -> Dict:
        """Извлечение всех данных о матче: embed плеер, Ace Stream, Web плееры"""
        result = {
            'embed_url': None,  # Прямая ссылка на embed плеер для iframe
            'acestreams': [],
            'web_players': [],
        }
        
        try:
            logger.info(f"🎥 Загрузка страницы матча: {match_url}")
            
            if not await self._init_browser():
                return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Извлекаем все данные
            page_data = await self.page.evaluate("""
            () => {
                const result = {
                    webplayerUrls: [],
                    acestreams: []
                };
                
                // 1. Ищем все onclick с show_webplayer - это ссылки на плееры
                document.querySelectorAll('[onclick]').forEach(el => {
                    const onclick = el.getAttribute('onclick') || '';
                    const href = el.href || '';
                    
                    if (onclick.includes('show_webplayer')) {
                        // URL из href или из onclick
                        if (href && href.includes('webplayer')) {
                            result.webplayerUrls.push(href);
                        }
                    }
                });
                
                // 2. Ищем ссылки на webplayer2.php напрямую
                document.querySelectorAll('a[href*="webplayer"]').forEach(link => {
                    const href = link.href;
                    if (href && href.includes('webplayer') && !href.includes('ads')) {
                        result.webplayerUrls.push(href);
                    }
                });
                
                // 3. Ищем iframe с плеером
                document.querySelectorAll('iframe').forEach(iframe => {
                    const src = iframe.src || '';
                    if (src.includes('emb.apl') || src.includes('player/live') || src.includes('player/video')) {
                        result.webplayerUrls.push(src);
                    }
                });
                
                // 4. Ace Stream
                const html = document.body.innerHTML;
                const aceMatches = html.matchAll(/acestream:\\/\\/([a-f0-9]{40})/gi);
                for (const m of aceMatches) {
                    result.acestreams.push('acestream://' + m[1]);
                }
                
                if (result.acestreams.length === 0) {
                    const hexMatches = html.matchAll(/["']([a-f0-9]{40})["']/gi);
                    for (const m of hexMatches) {
                        result.acestreams.push('acestream://' + m[1]);
                    }
                }
                
                return result;
            }
            """)
            
            webplayer_urls = list(set(page_data.get('webplayerUrls', [])))
            result['acestreams'] = list(set(page_data.get('acestreams', [])))
            
            logger.info(f"📊 Найдено webplayer URL: {len(webplayer_urls)}")
            
            # Если есть webplayer URL - загружаем и извлекаем embed
            if webplayer_urls:
                for wp_url in webplayer_urls[:3]:  # Пробуем первые 3
                    embed_url = await self._extract_embed_from_webplayer(wp_url)
                    if embed_url:
                        result['embed_url'] = embed_url
                        result['web_players'].append(embed_url)
                        logger.info(f"✅ Найден embed URL: {embed_url}")
                        break  # Берём первый рабочий
            
            logger.info(f"✅ Результат: embed={result['embed_url'] is not None}, acestreams={len(result['acestreams'])}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных матча: {e}")
        
        return result
    
    async def _extract_embed_from_webplayer(self, webplayer_url: str) -> Optional[str]:
        """Извлечение embed URL из webplayer страницы"""
        try:
            logger.info(f"🎬 Загрузка webplayer: {webplayer_url[:60]}...")
            
            # Make URL absolute
            if webplayer_url.startswith('//'):
                webplayer_url = 'https:' + webplayer_url
            elif not webplayer_url.startswith('http'):
                webplayer_url = 'https://' + webplayer_url
            
            player_page = await self.context.new_page()
            
            try:
                await player_page.goto(webplayer_url, wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(2)
                
                # Ищем iframe с embed плеером
                embed_url = await player_page.evaluate("""
                () => {
                    // Ищем iframe с emb.apl
                    const iframes = document.querySelectorAll('iframe');
                    for (const iframe of iframes) {
                        const src = iframe.src || '';
                        if (src.includes('emb.apl') && (src.includes('player/live') || src.includes('player/video'))) {
                            return src;
                        }
                    }
                    return null;
                }
                """)
                
                if embed_url:
                    logger.info(f"✅ Embed: {embed_url}")
                    return embed_url
                
            finally:
                await player_page.close()
                
        except Exception as e:
            logger.warning(f"Ошибка webplayer: {e}")
        
        return None

    async def get_match_acestreams(self, match_url: str) -> List[str]:
        """Извлечение только Ace Stream ссылок (для обратной совместимости)"""
        data = await self.get_match_data(match_url)
        return data.get('acestreams', [])
