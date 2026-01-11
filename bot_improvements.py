# Рекомендации по улучшению бота для FutLive
# Применить эти изменения к вашему bot.py на GitHub

"""
КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:

1. ПЕРЕДАЧА ДАННЫХ В WEB APP (Строка ~161)
   
   ❌ ТЕКУЩИЙ КОД (НЕПРАВИЛЬНО):
   ```python
   web_app_info = types.WebAppInfo(url=f"{WEB_APP_URL}?link={link}&title={title}&channels={json.dumps(channels)}")
   ```
   
   ✅ ИСПРАВЛЕННЫЙ КОД:
   ```python
   # Передаем только ID матча, Web App сам запросит ссылки через API
   web_app_info = types.WebAppInfo(
       url=f"{WEB_APP_URL}?match_id={match_id}&channel={channel_index}"
   )
   ```

2. TIMEOUT ПРИ ПАРСИНГЕ (Добавить в parser.py)
   ```python
   import signal
   
   def timeout_handler(signum, frame):
       raise TimeoutError("Парсинг занял слишком много времени")
   
   def get_streams_with_timeout(match_url, timeout=10):
       signal.signal(signal.SIGALRM, timeout_handler)
       signal.alarm(timeout)
       try:
           streams = get_streams(match_url)
           signal.alarm(0)  # Отменить таймер
           return streams
       except TimeoutError:
           return []
   ```

3. КЭШИРОВАНИЕ МАТЧЕЙ (Добавить в bot.py)
   ```python
   from functools import lru_cache
   from datetime import datetime, timedelta
   
   class MatchCache:
       def __init__(self, ttl_minutes=30):
           self.cache = {}
           self.ttl = timedelta(minutes=ttl_minutes)
       
       def get(self, key):
           if key in self.cache:
               data, timestamp = self.cache[key]
               if datetime.now() - timestamp < self.ttl:
                   return data
               del self.cache[key]
           return None
       
       def set(self, key, value):
           self.cache[key] = (value, datetime.now())
       
       def clear_old(self):
           now = datetime.now()
           expired = [k for k, (_, t) in self.cache.items() if now - t > self.ttl]
           for k in expired:
               del self.cache[k]
   
   match_cache = MatchCache()
   ```

4. ОБРАБОТКА ОШИБОК IFRAME (Добавить в web_app.html)
   ```javascript
   iframe.onerror = function() {
       showError('Видео недоступно', 'Сервер плеера недоступен');
   };
   
   iframe.onload = function() {
       try {
           // Проверяем, загрузился ли контент
           const doc = iframe.contentDocument || iframe.contentWindow.document;
           if (doc && doc.body && doc.body.innerHTML.includes('404')) {
               showError('Видео не найдено', 'Попробуйте другой канал');
           }
       } catch (e) {
           // CORS ошибка - это нормально
           console.log('CORS ограничение (ожидается)');
       }
   };
   ```

5. FALLBACK ДЛЯ НЕРАБОТАЮЩИХ ПЛЕЕРОВ
   ```python
   # В parser.py добавить альтернативные источники
   FALLBACK_SOURCES = [
       'https://gooool365.org/',
       'https://gol365.online/',
       'https://golmedia.net/'
   ]
   
   def get_streams_with_fallback(match_url):
       streams = get_streams(match_url)
       if not streams:
           # Пробуем альтернативные источники
           for source in FALLBACK_SOURCES:
               try:
                   streams = get_streams(source + match_url.split('/')[-1])
                   if streams:
                       return streams
               except:
                   continue
       return streams
   ```

ОПТИМИЗАЦИИ:

1. Асинхронный парсинг (использовать asyncio)
2. Кэширование результатов на 30 минут
3. Ограничение размера кэша (max 100 матчей)
4. Логирование всех ошибок в файл
5. Graceful shutdown при перезагрузке

РЕКОМЕНДУЕМАЯ СТРУКТУРА bot.py:

```python
import asyncio
import logging
from datetime import datetime, timedelta
from functools import lru_cache

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Кэш
class MatchCache:
    def __init__(self, ttl_minutes=30, max_size=100):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            del self.cache[key]
        return None
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]
        self.cache[key] = (value, datetime.now())

match_cache = MatchCache()

# Асинхронный парсинг
async def get_matches_async():
    try:
        matches = await asyncio.to_thread(get_matches)
        match_cache.set('matches', matches)
        return matches
    except Exception as e:
        logger.error(f'Ошибка парсинга матчей: {e}')
        return match_cache.get('matches') or []

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    try:
        matches = await get_matches_async()
        if not matches:
            await message.reply('Матчи не найдены. Попробуйте позже.')
            return
        # ... остальной код
    except Exception as e:
        logger.error(f'Ошибка в start: {e}')
        await message.reply('Произошла ошибка. Попробуйте позже.')
```

ТЕСТИРОВАНИЕ:

1. Проверить timeout при медленном интернете
2. Проверить fallback при недоступности основного источника
3. Проверить кэш при повторном запросе
4. Проверить обработку ошибок при пустом списке матчей
5. Проверить Web App на разных устройствах (iOS, Android, Desktop)

РАЗВЕРТЫВАНИЕ:

1. Обновить код на GitHub
2. Перезагрузить бота на сервере
3. Протестировать все функции
4. Добавить мониторинг ошибок (Sentry или аналог)
5. Настроить логирование в файл
"""

print(__doc__)
