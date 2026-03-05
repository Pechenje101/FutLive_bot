"""
Russian Sports Sources Parser
Парсер русскоязычных источников спортивных трансляций
"""

import asyncio
import logging
import re
import hashlib
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

SPORTS_RU = {
    'football': {'name': 'Футбол', 'emoji': '⚽'},
    'hockey': {'name': 'Хоккей', 'emoji': '🏒'},
    'tennis': {'name': 'Теннис', 'emoji': '🎾'},
    'basketball': {'name': 'Баскетбол', 'emoji': '🏀'},
    'volleyball': {'name': 'Волейбол', 'emoji': '🏐'},
    'handball': {'name': 'Гандбол', 'emoji': '🤝'},
    'mma': {'name': 'Единоборства', 'emoji': '🥊'},
}


class RussianSource(ABC):
    """Базовый класс русскоязычного источника"""
    
    def __init__(self):
        self.name = "Unknown"
        self.url = ""
        self.language = "ru"
    
    @abstractmethod
    async def get_matches(self, page) -> List[Dict]:
        """Получить список матчей"""
        pass
    
    @abstractmethod
    async def get_stream_url(self, page, match_url: str) -> Dict:
        """Получить URL трансляции"""
        pass


class LiveTVSource(RussianSource):
    """LiveTV.sx - основной русскоязычный источник"""
    
    def __init__(self):
        super().__init__()
        self.name = "LiveTV"
        self.url = "https://livetv.sx"
        self.emoji = "🔴"
    
    async def get_matches(self, page) -> List[Dict]:
        matches = []
        try:
            await page.goto("https://livetv.sx/allupcoming/", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)
            
            data = await page.evaluate("""
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
            
            for m in data:
                match_id = hashlib.md5(m['href'].encode()).hexdigest()[:10]
                title = re.sub(r'^\d{1,2}:\d{2}\s*', '', ' '.join(m['text'].split())).strip()
                
                matches.append({
                    'id': f"ltv_{match_id}",
                    'title': title,
                    'sport': self._detect_sport(title),
                    'time': self._extract_time(m['text']),
                    'status': '🔴 LIVE' if m['isLive'] else '⏱️ Скоро',
                    'url': m['href'],
                    'source': 'LiveTV',
                    'source_emoji': '🔴',
                })
            
            logger.info(f"LiveTV: {len(matches)} матчей")
            
        except Exception as e:
            logger.error(f"LiveTV error: {e}")
        
        return matches
    
    async def get_stream_url(self, page, match_url: str) -> Dict:
        result = {'embed_url': None, 'acestreams': [], 'hls_url': None}
        try:
            await page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await page.evaluate("""
            () => {
                const result = { embed_url: null, acestreams: [] };
                const html = document.body.innerHTML;
                
                // webplayer.php?t=ifr - основной embed
                const embedMatch = html.match(/["']([^"']*webplayer\\.php\\?t=ifr[^"']*)["']/i);
                if (embedMatch) {
                    result.embed_url = embedMatch[1].replace(/&amp;/g, '&');
                }
                
                // Ace Stream ссылки
                const aceMatches = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (aceMatches) result.acestreams = aceMatches;
                
                return result;
            }
            """)
            
            if data.get('embed_url'):
                url = data['embed_url']
                if url.startswith('//'):
                    url = 'https:' + url
                result['embed_url'] = url
                logger.info(f"LiveTV embed: {url[:60]}...")
            
            result['acestreams'] = data.get('acestreams', [])
            
        except Exception as e:
            logger.error(f"LiveTV stream error: {e}")
        
        return result
    
    def _detect_sport(self, title: str) -> str:
        t = title.lower()
        if any(w in t for w in ['хоккей', 'hockey', 'nhl', 'khl', 'кхл', 'нхл']):
            return 'hockey'
        if any(w in t for w in ['теннис', 'tennis', 'atp', 'wta']):
            return 'tennis'
        if any(w in t for w in ['баскетбол', 'basketball', 'nba', 'нба']):
            return 'basketball'
        if any(w in t for w in ['волейбол', 'volleyball']):
            return 'volleyball'
        if any(w in t for w in ['гандбол', 'handball']):
            return 'handball'
        return 'football'
    
    def _extract_time(self, text: str) -> str:
        m = re.search(r'(\d{1,2}):(\d{2})', text)
        return f"{m.group(1)}:{m.group(2)}" if m else "⏱️"


class TorrentTVSource(RussianSource):
    """Torrent-TV.ru - Ace Stream каналы"""
    
    def __init__(self):
        super().__init__()
        self.name = "Torrent-TV"
        self.url = "https://torrent-tv.ru"
        self.emoji = "🚀"
    
    async def get_matches(self, page) -> List[Dict]:
        """Получить список спортивных каналов"""
        matches = []
        try:
            await page.goto("https://torrent-tv.ru/sport", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('.channel-item, .channel').forEach(item => {
                    const nameEl = item.querySelector('.channel-name, .name, a');
                    const linkEl = item.querySelector('a[href*="channel"]');
                    const aceEl = item.querySelector('[data-acestream], [data-id]');
                    
                    if (nameEl) {
                        results.push({
                            name: nameEl.textContent.trim(),
                            href: linkEl ? linkEl.href : '',
                            acestream: aceEl ? (aceEl.dataset.acestream || aceEl.dataset.id) : null
                        });
                    }
                });
                return results;
            }
            """)
            
            for i, ch in enumerate(data[:20]):
                matches.append({
                    'id': f"ttv_{i}",
                    'title': f"📺 {ch['name']}",
                    'sport': 'football',
                    'time': '',
                    'status': '🟢 Онлайн',
                    'url': f"{self.url}/{ch['href']}" if ch['href'] else self.url,
                    'source': 'Torrent-TV',
                    'source_emoji': '🚀',
                    'acestream': ch.get('acestream'),
                })
            
            logger.info(f"Torrent-TV: {len(matches)} каналов")
            
        except Exception as e:
            logger.error(f"Torrent-TV error: {e}")
        
        return matches
    
    async def get_stream_url(self, page, match_url: str) -> Dict:
        result = {'embed_url': None, 'acestreams': []}
        try:
            await page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(1)
            
            data = await page.evaluate("""
            () => {
                const result = { acestreams: [] };
                const html = document.body.innerHTML;
                
                // Ace Stream ID
                const aceMatch = html.match(/acestream:\\/\\/([a-f0-9]{40})/i);
                if (aceMatch) {
                    result.acestreams.push('acestream://' + aceMatch[1]);
                }
                
                // Data attribute
                const aceData = document.querySelector('[data-acestream]');
                if (aceData) {
                    const id = aceData.dataset.acestream;
                    if (id && id.length === 40) {
                        result.acestreams.push('acestream://' + id);
                    }
                }
                
                return result;
            }
            """)
            
            result['acestreams'] = data.get('acestreams', [])
            
        except Exception as e:
            logger.error(f"Torrent-TV stream error: {e}")
        
        return result


class SportTVOnlineSource(RussianSource):
    """Sport-TV.online - онлайн ТВ каналы"""
    
    def __init__(self):
        super().__init__()
        self.name = "Sport-TV"
        self.url = "https://sport-tv.online"
        self.emoji = "📺"
    
    async def get_matches(self, page) -> List[Dict]:
        """Получить список спортивных каналов"""
        matches = []
        
        # Предопределённые каналы
        channels = [
            {'name': 'Евроспорт 1', 'slug': 'evrosport-1', 'sport': 'multi'},
            {'name': 'Евроспорт 2', 'slug': 'evrosport-2', 'sport': 'multi'},
            {'name': 'Матч ТВ', 'slug': 'matc-tv', 'sport': 'multi'},
            {'name': 'Беларусь 5', 'slug': 'belarus-5', 'sport': 'multi'},
            {'name': 'Футбол 1', 'slug': 'futbol-1', 'sport': 'football'},
            {'name': 'Футбол 2', 'slug': 'futbol-2', 'sport': 'football'},
        ]
        
        for i, ch in enumerate(channels):
            matches.append({
                'id': f"stv_{i}",
                'title': f"📺 {ch['name']}",
                'sport': ch['sport'],
                'time': '',
                'status': '🟢 Онлайн',
                'url': f"{self.url}/channel/{ch['slug']}.html",
                'source': 'Sport-TV',
                'source_emoji': '📺',
            })
        
        return matches
    
    async def get_stream_url(self, page, match_url: str) -> Dict:
        result = {'embed_url': None, 'acestreams': []}
        try:
            await page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await page.evaluate("""
            () => {
                const result = { embed_url: null };
                
                // Ищем iframe с плеером
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {
                    const src = iframe.src || iframe.getAttribute('data-src');
                    if (src && (src.includes('player') || src.includes('stream') || src.includes('embed'))) {
                        result.embed_url = src;
                        break;
                    }
                }
                
                // Ищем видео элемент
                if (!result.embed_url) {
                    const video = document.querySelector('video');
                    if (video && video.src) {
                        result.embed_url = video.src;
                    }
                }
                
                return result;
            }
            """)
            
            result['embed_url'] = data.get('embed_url')
            
        except Exception as e:
            logger.error(f"Sport-TV stream error: {e}")
        
        return result


class ArenaVisionSource(RussianSource):
    """ArenaVision.in - Ace Stream матчи"""
    
    def __init__(self):
        super().__init__()
        self.name = "ArenaVision"
        self.url = "https://arenavision.in"
        self.emoji = "🎯"
    
    async def get_matches(self, page) -> List[Dict]:
        matches = []
        try:
            await page.goto(f"{self.url}/schedule", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('tr, .match, .event').forEach(row => {
                    const timeEl = row.querySelector('.time, [class*="time"]');
                    const teamsEl = row.querySelector('.teams, .title, [class*="team"]');
                    const aceEl = row.querySelector('[data-acestream], .acestream');
                    
                    if (teamsEl) {
                        results.push({
                            time: timeEl ? timeEl.textContent.trim() : '',
                            teams: teamsEl.textContent.trim(),
                            acestream: aceEl ? aceEl.textContent.trim() : null
                        });
                    }
                });
                return results;
            }
            """)
            
            for i, m in enumerate(data[:15]):
                matches.append({
                    'id': f"av_{i}",
                    'title': m['teams'],
                    'sport': 'football',
                    'time': m['time'],
                    'status': '⏱️ Скоро',
                    'url': self.url,
                    'source': 'ArenaVision',
                    'source_emoji': '🎯',
                    'acestream': m.get('acestream'),
                })
            
            logger.info(f"ArenaVision: {len(matches)} матчей")
            
        except Exception as e:
            logger.error(f"ArenaVision error: {e}")
        
        return matches
    
    async def get_stream_url(self, page, match_url: str) -> Dict:
        # ArenaVision использует Ace Stream
        return {'embed_url': None, 'acestreams': []}


class MultiRussianParser:
    """Мульти-парсер русскоязычных источников"""
    
    def __init__(self):
        self.sources = [
            LiveTVSource(),
            # TorrentTVSource(),  # Требует JS для каналов
            SportTVOnlineSource(),
            # ArenaVisionSource(),  # Требует JS
        ]
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def _init_browser(self):
        if self.page:
            return True
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                locale='ru-RU'
            )
            self.page = await self.context.new_page()
            return True
        except Exception as e:
            logger.error(f"Browser init error: {e}")
            return False
    
    async def get_all_matches(self) -> List[Dict]:
        """Получить матчи из всех русскоязычных источников"""
        if not await self._init_browser():
            return []
        
        all_matches = []
        
        for source in self.sources:
            try:
                matches = await source.get_matches(self.page)
                all_matches.extend(matches)
            except Exception as e:
                logger.error(f"Source {source.name} error: {e}")
        
        # Сортировка: LIVE сначала
        all_matches.sort(key=lambda x: (0 if 'LIVE' in x.get('status', '') or 'Онлайн' in x.get('status', '') else 1, x.get('time', '')))
        
        return all_matches
    
    async def get_stream_url(self, match: Dict) -> Dict:
        """Получить URL трансляции"""
        source_name = match.get('source', 'LiveTV')
        match_url = match.get('url', '')
        
        if not await self._init_browser():
            return {'embed_url': None, 'acestreams': []}
        
        for source in self.sources:
            if source.name == source_name:
                return await source.get_stream_url(self.page, match_url)
        
        # По умолчанию LiveTV
        return await self.sources[0].get_stream_url(self.page, match_url)
    
    async def close(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self._playwright: await self._playwright.stop()
        except: pass
        self.page = self.context = self.browser = self._playwright = None


# Экспорт для использования в боте
def get_sports_emoji(sport: str) -> str:
    return SPORTS_RU.get(sport, {}).get('emoji', '⚽')


def get_sports_name(sport: str) -> str:
    return SPORTS_RU.get(sport, {}).get('name', 'Футбол')
