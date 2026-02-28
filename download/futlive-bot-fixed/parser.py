import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from urllib.parse import urljoin, urlparse

# Настройка логирования для парсера
logger = logging.getLogger(__name__)

class GoooolParser:
    # Список альтернативных доменов
    BASE_URLS = [
        "https://gooool365.org",
        "https://gooool365.com", 
        "https://gooool365.net",
        "https://gooool365.tv"
    ]
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://gooool365.org/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'max-age=0',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # Отключаем проверку SSL для некоторых проблемных сайтов
        self.session.verify = False
        # Добавляем адаптер с retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Определяем рабочий домен
        self.base_url = self._find_working_domain()
        
    def _find_working_domain(self):
        """Находит рабочий домен из списка альтернатив"""
        import time
        
        for url in self.BASE_URLS:
            try:
                logger.info(f"Проверка домена: {url}")
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    logger.info(f"✅ Рабочий домен найден: {url}")
                    return url
                else:
                    logger.warning(f"❌ Домен {url} вернул {response.status_code}")
            except Exception as e:
                logger.warning(f"❌ Ошибка при проверке {url}: {e}")
            time.sleep(0.5)
        
        # Если ни один домен не работает, используем первый
        logger.warning("⚠️ Ни один домен не отвечает, используем первый из списка")
        return self.BASE_URLS[0]

    def get_matches(self):
        try:
            print(f"[PARSER] Загрузка матчей с {self.base_url}")
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            matches = []
            # Ищем все ссылки на матчи
            links = soup.find_all('a', href=re.compile(r'/online/\d+'))

            seen_urls = set()
            for link in links:
                title = link.get_text(strip=True)
                if not title:
                    # Если текст пустой, ищем в дочерних элементах
                    title_parts = []
                    for child in link.descendants:
                        if isinstance(child, str) and child.strip():
                            title_parts.append(child.strip())
                    title = ' '.join(title_parts)
                
                url = link.get('href')
                if not url:
                    continue
                    
                if not url.startswith('http'):
                    url = self.base_url + url
                
                # Фильтруем только прямые трансляции
                if title and url and url not in seen_urls:
                    if re.search(r'/online/\d+-', url):
                        matches.append({'title': title, 'url': url})
                        seen_urls.add(url)
                        print(f"[PARSER] Найден матч: {title}")
            
            print(f"[PARSER] Всего найдено {len(matches)} матчей")
            return matches
        except Exception as e:
            print(f"[PARSER] Ошибка при получении матчей: {e}")
            return []

    def get_links(self, match_url):
        try:
            print(f"[PARSER] Получение ссылок для: {match_url}")
            links = []
            
            # 1. Получаем основную страницу матча
            main_resp = self.session.get(match_url, timeout=15)
            main_resp.raise_for_status()
            main_resp.encoding = 'utf-8'
            main_html = main_resp.text
            
            # Ищем заголовок матча
            soup = BeautifulSoup(main_html, 'html.parser')
            title_tag = soup.find('h1') or soup.find('title')
            match_title = title_tag.get_text(strip=True) if title_tag else 'Матч'
            
            # 2. Ищем iframe на странице матча
            iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>', main_html, re.IGNORECASE)
            for i, src in enumerate(iframes):
                # Пропускаем служебные iframe
                if any(x in src.lower() for x in ['google', 'yandex', 'cackle', 'vk.com', 'facebook', 'twitter', 'instagram', 'metrika', 'analytics']):
                    continue
                if src.startswith('//'): 
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = self.base_url + src
                
                # Проверяем доступность ссылки
                if self._is_url_accessible(src):
                    links.append({
                        'type': 'web', 
                        'title': f'Трансляция {i+1}', 
                        'url': src,
                        'source': 'iframe'
                    })
                    print(f"[PARSER] Найден iframe: {src[:100]}...")
            
            # 3. Ищем переменные с видео в скриптах
            video_vars = re.findall(r'videoid\d+\s*=\s*[\'"](.*?)[\'"]', main_html, re.DOTALL)
            for i, video_html in enumerate(video_vars):
                src_match = re.search(r'src=["\'](.*?)["\']', video_html)
                if src_match:
                    url = src_match.group(1)
                    if url.startswith('//'): 
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = self.base_url + url
                    
                    if self._is_url_accessible(url):
                        links.append({
                            'type': 'web', 
                            'title': f'Канал {i+1}', 
                            'url': url,
                            'source': 'script'
                        })
                        print(f"[PARSER] Найден видеопоток из скрипта: {url[:100]}...")
            
            # 4. POST запрос к /player/ для получения дополнительных ссылок
            newsid_match = re.search(r'/online/(\d+)-', match_url)
            if newsid_match:
                newsid = newsid_match.group(1)
                player_url = f"{self.base_url}/player/"
                data = {'newsid': newsid}
                
                headers = self.HEADERS.copy()
                headers['Referer'] = match_url
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
                
                try:
                    player_resp = self.session.post(player_url, data=data, headers=headers, timeout=15)
                    player_resp.raise_for_status()
                    player_resp.encoding = 'utf-8'
                    player_html = player_resp.text
                    
                    # Ищем Ace Stream ссылки
                    acestream_pattern = r'acestream://([a-f0-9]{40})'
                    ace_ids = re.findall(acestream_pattern, player_html)
                    
                    # Ищем ссылки Ace Stream с названиями
                    soup_player = BeautifulSoup(player_html, 'html.parser')
                    ace_tags = soup_player.find_all('a', href=re.compile(r'acestream://'))
                    
                    for tag in ace_tags:
                        title = tag.get_text(strip=True) or "Ace Stream"
                        href = tag.get('href')
                        if href:
                            links.append({
                                'type': 'acestream', 
                                'title': title, 
                                'url': href,
                                'source': 'player_api'
                            })
                            print(f"[PARSER] Найден Ace Stream: {title}")
                    
                    if not ace_tags and ace_ids:
                        for i, ace_id in enumerate(ace_ids):
                            links.append({
                                'type': 'acestream', 
                                'title': f'Ace Stream {i+1}', 
                                'url': f'acestream://{ace_id}',
                                'source': 'player_api'
                            })
                            print(f"[PARSER] Найден Ace Stream ID: {ace_id}")
                    
                    # Ищем дополнительные iframe в ответе /player/
                    player_iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>', player_html, re.IGNORECASE)
                    for i, src in enumerate(player_iframes):
                        if src.startswith('//'): 
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = self.base_url + src
                        
                        if self._is_url_accessible(src):
                            links.append({
                                'type': 'web', 
                                'title': f'Доп. канал {i+1}', 
                                'url': src,
                                'source': 'player_iframe'
                            })
                            print(f"[PARSER] Найден доп. iframe: {src[:100]}...")
                            
                except Exception as e:
                    print(f"[PARSER] Ошибка при запросе к /player/: {e}")
            
            # 5. Ищем ссылки на сторонние плееры
            # Паттерны для поиска URL плееров
            player_patterns = [
                r'https?://[^\s\'"]+\.php[^\s\'"]*',
                r'https?://[^\s\'"]+/player[^\s\'"]*',
                r'https?://[^\s\'"]+/embed/[^\s\'"]*',
                r'https?://[^\s\'"]+/live/[^\s\'"]*',
                r'https?://[^\s\'"]+/stream[^\s\'"]*',
            ]
            
            for pattern in player_patterns:
                external_links = re.findall(pattern, main_html, re.IGNORECASE)
                for url in external_links:
                    # Фильтруем служебные URL
                    if any(x in url.lower() for x in ['gooool365.org', 'yandex', 'google', 'schema.org', 'javascript']): 
                        continue
                    
                    if self._is_url_accessible(url):
                        links.append({
                            'type': 'web', 
                            'title': f'Плеер {len(links)+1}', 
                            'url': url,
                            'source': 'external'
                        })
                        print(f"[PARSER] Найден внешний плеер: {url[:100]}...")
                        break  # Берем только первое совпадение каждого типа
            
            # 6. Убираем дубликаты
            unique_links = []
            seen_urls = set()
            for link in links:
                if link['url'] and link['url'] not in seen_urls:
                    seen_urls.add(link['url'])
                    unique_links.append(link)
            
            print(f"[PARSER] Всего найдено {len(unique_links)} уникальных ссылок")
            return unique_links
            
        except Exception as e:
            print(f"[PARSER] Ошибка при получении ссылок: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _is_url_accessible(self, url):
        """Проверяет доступность URL"""
        try:
            # Для тестирования берем только HEAD запрос
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False

if __name__ == "__main__":
    parser = GoooolParser()
    print("=== Тестирование парсера ===")
    matches = parser.get_matches()
    if matches:
        match = matches[0]
        print(f"\nАнализ матча: {match['title']}")
        print(f"URL: {match['url']}")
        links = parser.get_links(match['url'])
        print(f"\nНайдено ссылок: {len(links)}")
        for link in links:
            print(f"- {link['type']}: {link['title']} ({link['url'][:80]}...)")
    else:
        print("Матчи не найдены")
