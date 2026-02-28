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
        title = ' '.join(title.split())
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
        """Извлечение всех данных о матче: Ace Stream, Web плееры, прямые ссылки"""
        result = {
            'acestreams': [],
            'web_players': [],
            'video_url': None,
            'hls_url': None,
        }
        
        try:
            logger.info(f"🎥 Загрузка страницы матча: {match_url}")
            
            if not await self._init_browser():
                return result
            
            # Load match page
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Extract all data via JavaScript
            page_data = await self.page.evaluate("""
            () => {
                const result = {
                    acestreams: [],
                    webPlayers: [],
                    videoUrl: null,
                    hlsUrl: null
                };
                
                const html = document.body.innerHTML;
                
                // 1. Ace Stream IDs
                const aceMatches = html.matchAll(/acestream:\\/\\/([a-f0-9]{40})/gi);
                for (const m of aceMatches) {
                    result.acestreams.push('acestream://' + m[1]);
                }
                
                // Also find 40-char hex strings that might be acestream IDs
                if (result.acestreams.length === 0) {
                    const hexMatches = html.matchAll(/["']([a-f0-9]{40})["']/gi);
                    for (const m of hexMatches) {
                        result.acestreams.push('acestream://' + m[1]);
                    }
                }
                
                // 2. Web player iframes (apl392.me, etc)
                document.querySelectorAll('iframe').forEach(iframe => {
                    const src = iframe.src || '';
                    if (src.includes('apl') || src.includes('player') || src.includes('video.php')) {
                        if (!src.includes('ads.') && !src.includes('banner')) {
                            result.webPlayers.push(src);
                        }
                    }
                });
                
                // 3. Links to video players
                document.querySelectorAll('a').forEach(link => {
                    const href = link.href || '';
                    if (href.includes('showvideo') || href.includes('video.php') || href.includes('player')) {
                        if (!href.includes('ads.')) {
                            result.webPlayers.push(href);
                        }
                    }
                });
                
                // 4. m3u8 URLs in scripts
                const m3u8Match = html.match(/["'](https?:\\/\\/[^"']*\\.m3u8[^"']*)["']/i);
                if (m3u8Match) {
                    result.hlsUrl = m3u8Match[1].replace(/\\\\/g, '');
                }
                
                // 5. mp4 URLs
                const mp4Match = html.match(/["'](https?:\\/\\/[^"']*\\.mp4[^"']*)["']/i);
                if (mp4Match) {
                    result.videoUrl = mp4Match[1].replace(/\\\\/g, '');
                }
                
                return result;
            }
            """)
            
            result['acestreams'] = list(set(page_data.get('acestreams', [])))
            result['web_players'] = list(set(page_data.get('webPlayers', [])))
            result['video_url'] = page_data.get('videoUrl')
            result['hls_url'] = page_data.get('hlsUrl')
            
            # If we have web player links, try to extract direct video URL
            if result['web_players'] and not result['video_url']:
                for player_url in result['web_players'][:2]:  # Try first 2
                    video_url = await self._extract_video_from_player(player_url)
                    if video_url:
                        result['video_url'] = video_url
                        break
            
            logger.info(f"✅ Найдено: acestreams={len(result['acestreams'])}, web_players={len(result['web_players'])}, video_url={result['video_url'] is not None}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных матча: {e}")
        
        return result
    
    async def _extract_video_from_player(self, player_url: str) -> Optional[str]:
        """Извлечение прямой ссылки на видео из плеера"""
        try:
            logger.info(f"🎬 Извлечение видео из плеера: {player_url}")
            
            # Make URL absolute
            if player_url.startswith('//'):
                player_url = 'https:' + player_url
            elif not player_url.startswith('http'):
                player_url = 'https://' + player_url
            
            # Open in new page to avoid affecting main page
            player_page = await self.context.new_page()
            
            try:
                await player_page.goto(player_url, wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(2)
                
                # Extract video URL
                video_data = await player_page.evaluate("""
                () => {
                    const result = {};
                    
                    // Video element
                    const video = document.querySelector('video');
                    if (video) {
                        result.video_src = video.src;
                        result.video_currentSrc = video.currentSrc;
                    }
                    
                    // Source elements
                    const sources = document.querySelectorAll('source');
                    sources.forEach(s => {
                        if (s.src && (s.src.includes('.mp4') || s.src.includes('.m3u8'))) {
                            result.source = s.src;
                        }
                    });
                    
                    // Scripts
                    const html = document.body.innerHTML;
                    
                    // mp4
                    const mp4Match = html.match(/["'](https?:\\/\\/[^"']*\\.mp4[^"']*)["']/i);
                    if (mp4Match) result.mp4 = mp4Match[1].replace(/\\\\/g, '');
                    
                    // m3u8
                    const m3u8Match = html.match(/["'](https?:\\/\\/[^"']*\\.m3u8[^"']*)["']/i);
                    if (m3u8Match) result.m3u8 = m3u8Match[1].replace(/\\\\/g, '');
                    
                    // file: "..." pattern
                    const fileMatch = html.match(/file\\s*:\\s*["']([^"']+)["']/i);
                    if (fileMatch) result.file = fileMatch[1];
                    
                    return result;
                }
                """)
                
                # Return first found video URL
                for key in ['video_currentSrc', 'video_src', 'source', 'mp4', 'm3u8', 'file']:
                    url = video_data.get(key)
                    if url and ('.mp4' in url or '.m3u8' in url):
                        # Clean URL
                        if url.startswith('//'):
                            url = 'https:' + url
                        logger.info(f"✅ Найдена ссылка на видео: {url[:80]}...")
                        return url
                
            finally:
                await player_page.close()
                
        except Exception as e:
            logger.warning(f"Не удалось извлечь видео из плеера: {e}")
        
        return None

    async def get_match_acestreams(self, match_url: str) -> List[str]:
        """Извлечение только Ace Stream ссылок (для обратной совместимости)"""
        data = await self.get_match_data(match_url)
        return data.get('acestreams', [])
