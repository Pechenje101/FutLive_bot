"""
Multi-Source Sports Parser
Парсер матчей из нескольких источников
"""

import asyncio
import logging
import re
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

SPORTS = {
    'football': {'name': 'Футбол', 'emoji': '⚽'},
    'hockey': {'name': 'Хоккей', 'emoji': '🏒'},
    'tennis': {'name': 'Теннис', 'emoji': '🎾'},
    'basketball': {'name': 'Баскетбол', 'emoji': '🏀'},
    'handball': {'name': 'Гандбол', 'emoji': '🤝'},
    'volleyball': {'name': 'Волейбол', 'emoji': '🏐'},
    'baseball': {'name': 'Бейсбол', 'emoji': '⚾'},
    'mma': {'name': 'MMA/Бокс', 'emoji': '🥊'},
    'cricket': {'name': 'Крикет', 'emoji': '🏏'},
    'american_football': {'name': 'Ам. футбол', 'emoji': '🏈'},
}


class BaseSource(ABC):
    """Базовый класс для источника"""
    
    def __init__(self):
        self.name = "Unknown"
        self.url = ""
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    @abstractmethod
    async def get_matches(self) -> List[Dict]:
        """Получить список матчей"""
        pass
    
    @abstractmethod
    async def get_stream_url(self, match_url: str) -> Dict:
        """Получить URL трансляции"""
        pass
    
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
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = await self.context.new_page()
            return True
        except Exception as e:
            logger.error(f"Browser init error: {e}")
            return False
    
    async def close(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self._playwright: await self._playwright.stop()
        except: pass


class LiveTVSource(BaseSource):
    """LiveTV.sx - основной источник"""
    
    def __init__(self):
        super().__init__()
        self.name = "LiveTV"
        self.url = "https://livetv.sx"
    
    async def get_matches(self) -> List[Dict]:
        matches = []
        try:
            if not await self._init_browser():
                return []
            
            await self.page.goto("https://livetv.sx/allupcoming/", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)
            
            data = await self.page.evaluate("""
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
                    'status': '🔴 LIVE' if m['isLive'] else '⏱️ UPCOMING',
                    'url': m['href'],
                    'source': 'LiveTV',
                })
            
        except Exception as e:
            logger.error(f"LiveTV error: {e}")
        
        return matches
    
    async def get_stream_url(self, match_url: str) -> Dict:
        result = {'embed_url': None, 'acestreams': []}
        try:
            if not await self._init_browser():
                return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await self.page.evaluate("""
            () => {
                const result = { embed_url: null, acestreams: [] };
                const html = document.body.innerHTML;
                
                // webplayer.php
                const embedMatch = html.match(/["']([^"']*webplayer\\.php\\?t=ifr[^"']*)["']/i);
                if (embedMatch) {
                    result.embed_url = embedMatch[1].replace(/&amp;/g, '&');
                }
                
                // Ace Stream
                const aceMatches = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (aceMatches) {
                    result.acestreams = aceMatches;
                }
                
                return result;
            }
            """)
            
            if data.get('embed_url'):
                url = data['embed_url']
                if url.startswith('//'):
                    url = 'https:' + url
                result['embed_url'] = url
            
            result['acestreams'] = data.get('acestreams', [])
            
        except Exception as e:
            logger.error(f"LiveTV stream error: {e}")
        
        return result
    
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


class CricfreeSource(BaseSource):
    """Cricfree - хорошее качество стримов"""
    
    def __init__(self):
        super().__init__()
        self.name = "Cricfree"
        self.url = "https://cricfree.sc"
    
    async def get_matches(self) -> List[Dict]:
        matches = []
        try:
            if not await self._init_browser():
                return []
            
            await self.page.goto(self.url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await self.page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('a[href*="/watch/"]').forEach(link => {
                    const text = link.textContent.trim();
                    const href = link.href;
                    if (text && href && text.length > 5) {
                        results.push({ text, href });
                    }
                });
                return results;
            }
            """)
            
            for i, m in enumerate(data[:30]):
                title = ' '.join(m['text'].split())
                matches.append({
                    'id': f"cf_{hashlib.md5(m['href'].encode()).hexdigest()[:8]}",
                    'title': title,
                    'sport': self._detect_sport(title),
                    'time': '',
                    'status': '🔴 LIVE',
                    'url': m['href'],
                    'source': 'Cricfree',
                })
            
        except Exception as e:
            logger.error(f"Cricfree error: {e}")
        
        return matches
    
    async def get_stream_url(self, match_url: str) -> Dict:
        result = {'embed_url': None, 'acestreams': []}
        try:
            if not await self._init_browser():
                return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await self.page.evaluate("""
            () => {
                const result = { embed_url: null };
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {
                    const src = iframe.src || iframe.getAttribute('data-src');
                    if (src && (src.includes('stream') || src.includes('player') || src.includes('embed'))) {
                        result.embed_url = src;
                        break;
                    }
                }
                return result;
            }
            """)
            
            result['embed_url'] = data.get('embed_url')
            
        except Exception as e:
            logger.error(f"Cricfree stream error: {e}")
        
        return result
    
    def _detect_sport(self, title: str) -> str:
        t = title.lower()
        if 'cricket' in t: return 'cricket'
        if 'football' in t and 'american' not in t: return 'football'
        if 'soccer' in t: return 'football'
        if 'basketball' in t or 'nba' in t: return 'basketball'
        if 'tennis' in t: return 'tennis'
        if 'hockey' in t or 'nhl' in t: return 'hockey'
        if 'mma' in t or 'ufc' in t or 'boxing' in t: return 'mma'
        if 'nfl' in t or 'american football' in t: return 'american_football'
        if 'baseball' in t or 'mlb' in t: return 'baseball'
        return 'football'


class SportRARSource(BaseSource):
    """SportRAR - похож на LiveTV"""
    
    def __init__(self):
        super().__init__()
        self.name = "SportRAR"
        self.url = "https://sportrar.tv"
    
    async def get_matches(self) -> List[Dict]:
        matches = []
        try:
            if not await self._init_browser():
                return []
            
            await self.page.goto(self.url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await self.page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('a[href*="/event/"]').forEach(link => {
                    const text = link.textContent.trim();
                    const href = link.href;
                    if (text && href) {
                        const parent = link.closest('.event') || link.parentElement;
                        const isLive = parent && parent.className.includes('live');
                        results.push({ text, href, isLive });
                    }
                });
                return results;
            }
            """)
            
            for m in data[:30]:
                matches.append({
                    'id': f"sr_{hashlib.md5(m['href'].encode()).hexdigest()[:8]}",
                    'title': ' '.join(m['text'].split()),
                    'sport': 'football',
                    'time': '',
                    'status': '🔴 LIVE' if m.get('isLive') else '⏱️ UPCOMING',
                    'url': m['href'],
                    'source': 'SportRAR',
                })
            
        except Exception as e:
            logger.error(f"SportRAR error: {e}")
        
        return matches
    
    async def get_stream_url(self, match_url: str) -> Dict:
        # Похож на LiveTV
        result = {'embed_url': None, 'acestreams': []}
        try:
            if not await self._init_browser():
                return result
            
            await self.page.goto(match_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            data = await self.page.evaluate("""
            () => {
                const result = { embed_url: null, acestreams: [] };
                const html = document.body.innerHTML;
                
                // iframe src
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {
                    const src = iframe.src;
                    if (src) {
                        result.embed_url = src;
                        break;
                    }
                }
                
                // Ace Stream
                const aceMatches = html.match(/acestream:\\/\\/([a-f0-9]{40})/gi);
                if (aceMatches) result.acestreams = aceMatches;
                
                return result;
            }
            """)
            
            result['embed_url'] = data.get('embed_url')
            result['acestreams'] = data.get('acestreams', [])
            
        except Exception as e:
            logger.error(f"SportRAR stream error: {e}")
        
        return result


class MultiSourceParser:
    """Мульти-источник парсер"""
    
    def __init__(self):
        self.sources = [
            LiveTVSource(),
            CricfreeSource(),
            SportRARSource(),
        ]
        self._initialized = False
    
    async def get_all_matches(self) -> List[Dict]:
        """Получить матчи из всех источников"""
        all_matches = []
        
        # Параллельный запрос к источникам
        tasks = [source.get_matches() for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Source {self.sources[i].name} error: {result}")
            elif result:
                all_matches.extend(result)
        
        # Сортировка: LIVE primero
        all_matches.sort(key=lambda x: (0 if 'LIVE' in x['status'] else 1, x.get('time', '')))
        
        return all_matches
    
    async def get_stream_url(self, match: Dict) -> Dict:
        """Получить URL трансляции для матча"""
        source_name = match.get('source', 'LiveTV')
        match_url = match.get('url', '')
        
        # Найти нужный источник
        for source in self.sources:
            if source.name == source_name or source_name == 'LiveTV':
                return await source.get_stream_url(match_url)
        
        return {'embed_url': None, 'acestreams': []}
    
    async def close(self):
        for source in self.sources:
            await source.close()


# Тест
async def test():
    parser = MultiSourceParser()
    
    print("🔍 Загрузка матчей из всех источников...\n")
    matches = await parser.get_all_matches()
    
    print(f"✅ Всего матчей: {len(matches)}\n")
    
    # Группировка по источнику
    by_source = {}
    for m in matches:
        by_source.setdefault(m['source'], []).append(m)
    
    for source, ms in by_source.items():
        print(f"📡 {source}: {len(ms)} матчей")
        for m in ms[:3]:
            print(f"   - {m['title'][:40]}...")
        print()
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test())
