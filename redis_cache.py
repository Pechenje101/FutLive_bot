#!/usr/bin/env python3
"""
Redis кэш для хранения матчей и каналов
Обеспечивает быстрый доступ к данным и масштабируемость
"""

import redis
import json
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class RedisCache:
    """Класс для работы с Redis кэшем"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """Инициализация Redis клиента"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            # Проверяем соединение
            self.redis_client.ping()
            logger.info(f"✅ Redis подключен: {host}:{port}")
            self.connected = True
        except Exception as e:
            logger.warning(f"⚠️ Redis не доступен: {e}. Используем локальный кэш.")
            self.redis_client = None
            self.connected = False
            self.local_cache = {}
    
    def is_connected(self) -> bool:
        """Проверить, подключен ли Redis"""
        return self.connected
    
    # ============ МАТЧИ ============
    
    def set_matches(self, matches: List[Dict], ttl: int = 300) -> bool:
        """
        Сохранить матчи в кэш
        
        Args:
            matches: Список матчей
            ttl: Время жизни в секундах (по умолчанию 5 минут)
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if self.connected:
                data = json.dumps(matches, ensure_ascii=False)
                self.redis_client.setex('matches', ttl, data)
                logger.info(f"💾 Матчи сохранены в Redis ({len(matches)} шт, TTL: {ttl}s)")
            else:
                self.local_cache['matches'] = matches
                logger.info(f"💾 Матчи сохранены в локальный кэш ({len(matches)} шт)")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении матчей: {e}")
            return False
    
    def get_matches(self) -> Optional[List[Dict]]:
        """
        Получить матчи из кэша
        
        Returns:
            Список матчей или None если не найдены
        """
        try:
            if self.connected:
                data = self.redis_client.get('matches')
                if data:
                    matches = json.loads(data)
                    logger.info(f"📦 Матчи получены из Redis ({len(matches)} шт)")
                    return matches
            else:
                if 'matches' in self.local_cache:
                    matches = self.local_cache['matches']
                    logger.info(f"📦 Матчи получены из локального кэша ({len(matches)} шт)")
                    return matches
        except Exception as e:
            logger.error(f"❌ Ошибка при получении матчей: {e}")
        
        return None
    
    def delete_matches(self) -> bool:
        """Удалить матчи из кэша"""
        try:
            if self.connected:
                self.redis_client.delete('matches')
            else:
                self.local_cache.pop('matches', None)
            logger.info("🗑️ Матчи удалены из кэша")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении матчей: {e}")
            return False
    
    # ============ КАНАЛЫ ============
    
    def set_channels(self, match_id: int, channels: Dict, ttl: int = 300) -> bool:
        """
        Сохранить каналы матча в кэш
        
        Args:
            match_id: ID матча
            channels: Словарь каналов
            ttl: Время жизни в секундах
        
        Returns:
            True если успешно
        """
        try:
            key = f'channels:{match_id}'
            if self.connected:
                data = json.dumps(channels, ensure_ascii=False)
                self.redis_client.setex(key, ttl, data)
                logger.info(f"💾 Каналы матча {match_id} сохранены в Redis ({len(channels)} шт)")
            else:
                self.local_cache[key] = channels
                logger.info(f"💾 Каналы матча {match_id} сохранены в локальный кэш")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении каналов: {e}")
            return False
    
    def get_channels(self, match_id: int) -> Optional[Dict]:
        """
        Получить каналы матча из кэша
        
        Args:
            match_id: ID матча
        
        Returns:
            Словарь каналов или None
        """
        try:
            key = f'channels:{match_id}'
            if self.connected:
                data = self.redis_client.get(key)
                if data:
                    channels = json.loads(data)
                    logger.info(f"📦 Каналы матча {match_id} получены из Redis ({len(channels)} шт)")
                    return channels
            else:
                if key in self.local_cache:
                    channels = self.local_cache[key]
                    logger.info(f"📦 Каналы матча {match_id} получены из локального кэша")
                    return channels
        except Exception as e:
            logger.error(f"❌ Ошибка при получении каналов: {e}")
        
        return None
    
    def delete_channels(self, match_id: int) -> bool:
        """Удалить каналы матча из кэша"""
        try:
            key = f'channels:{match_id}'
            if self.connected:
                self.redis_client.delete(key)
            else:
                self.local_cache.pop(key, None)
            logger.info(f"🗑️ Каналы матча {match_id} удалены из кэша")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении каналов: {e}")
            return False
    
    # ============ ИЗБРАННЫЕ МАТЧИ ============
    
    def add_favorite(self, user_id: int, match_id: int) -> bool:
        """
        Добавить матч в избранное пользователя
        
        Args:
            user_id: ID пользователя Telegram
            match_id: ID матча
        
        Returns:
            True если успешно
        """
        try:
            key = f'favorites:{user_id}'
            if self.connected:
                self.redis_client.sadd(key, match_id)
                self.redis_client.expire(key, 86400 * 30)  # 30 дней
                logger.info(f"⭐ Матч {match_id} добавлен в избранное пользователя {user_id}")
            else:
                if key not in self.local_cache:
                    self.local_cache[key] = set()
                self.local_cache[key].add(match_id)
                logger.info(f"⭐ Матч {match_id} добавлен в локальное избранное")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении в избранное: {e}")
            return False
    
    def remove_favorite(self, user_id: int, match_id: int) -> bool:
        """Удалить матч из избранного"""
        try:
            key = f'favorites:{user_id}'
            if self.connected:
                self.redis_client.srem(key, match_id)
                logger.info(f"🗑️ Матч {match_id} удален из избранного пользователя {user_id}")
            else:
                if key in self.local_cache:
                    self.local_cache[key].discard(match_id)
                logger.info(f"🗑️ Матч {match_id} удален из локального избранного")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении из избранного: {e}")
            return False
    
    def get_favorites(self, user_id: int) -> List[int]:
        """Получить избранные матчи пользователя"""
        try:
            key = f'favorites:{user_id}'
            if self.connected:
                favorites = self.redis_client.smembers(key)
                result = [int(m) for m in favorites]
                logger.info(f"📦 Избранные матчи пользователя {user_id}: {len(result)} шт")
                return result
            else:
                if key in self.local_cache:
                    result = list(self.local_cache[key])
                    logger.info(f"📦 Избранные матчи из локального кэша: {len(result)} шт")
                    return result
        except Exception as e:
            logger.error(f"❌ Ошибка при получении избранных: {e}")
        
        return []
    
    # ============ УВЕДОМЛЕНИЯ ============
    
    def add_notification(self, user_id: int, match_id: int, match_title: str, notify_time: int) -> bool:
        """
        Добавить уведомление о матче
        
        Args:
            user_id: ID пользователя Telegram
            match_id: ID матча
            match_title: Название матча
            notify_time: Unix timestamp времени уведомления
        
        Returns:
            True если успешно
        """
        try:
            key = f'notifications:{user_id}:{match_id}'
            notification = {
                'user_id': user_id,
                'match_id': match_id,
                'match_title': match_title,
                'notify_time': notify_time,
                'created_at': int(time.time()),
                'sent': False
            }
            
            if self.connected:
                data = json.dumps(notification, ensure_ascii=False)
                # Сохраняем с TTL = время до уведомления + 1 час
                ttl = max(notify_time - int(time.time()) + 3600, 60)
                self.redis_client.setex(key, ttl, data)
                logger.info(f"🔔 Уведомление добавлено для пользователя {user_id}, матч {match_id}")
            else:
                self.local_cache[key] = notification
                logger.info(f"🔔 Уведомление добавлено в локальный кэш")
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении уведомления: {e}")
            return False
    
    def get_pending_notifications(self, current_time: Optional[int] = None) -> List[Dict]:
        """
        Получить все уведомления, которые нужно отправить
        
        Args:
            current_time: Текущее время (по умолчанию текущее время)
        
        Returns:
            Список уведомлений
        """
        if current_time is None:
            current_time = int(time.time())
        
        notifications = []
        
        try:
            if self.connected:
                # Ищем все ключи уведомлений
                pattern = 'notifications:*'
                keys = self.redis_client.keys(pattern)
                
                for key in keys:
                    data = self.redis_client.get(key)
                    if data:
                        notification = json.loads(data)
                        # Проверяем, пришло ли время отправки и не отправлено ли уже
                        if (notification['notify_time'] <= current_time and 
                            not notification.get('sent', False)):
                            notifications.append(notification)
                
                logger.info(f"📬 Найдено {len(notifications)} уведомлений для отправки")
            else:
                # Ищем в локальном кэше
                for key, notification in self.local_cache.items():
                    if key.startswith('notifications:'):
                        if (notification['notify_time'] <= current_time and 
                            not notification.get('sent', False)):
                            notifications.append(notification)
                
                logger.info(f"📬 Найдено {len(notifications)} уведомлений в локальном кэше")
        
        except Exception as e:
            logger.error(f"❌ Ошибка при получении уведомлений: {e}")
        
        return notifications
    
    def mark_notification_sent(self, user_id: int, match_id: int) -> bool:
        """Отметить уведомление как отправленное"""
        try:
            key = f'notifications:{user_id}:{match_id}'
            
            if self.connected:
                data = self.redis_client.get(key)
                if data:
                    notification = json.loads(data)
                    notification['sent'] = True
                    notification['sent_at'] = int(time.time())
                    updated_data = json.dumps(notification, ensure_ascii=False)
                    self.redis_client.set(key, updated_data)
                    logger.info(f"✅ Уведомление отмечено как отправленное")
            else:
                if key in self.local_cache:
                    self.local_cache[key]['sent'] = True
                    self.local_cache[key]['sent_at'] = int(time.time())
                    logger.info(f"✅ Уведомление отмечено в локальном кэше")
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при отметке уведомления: {e}")
            return False
    
    def delete_notification(self, user_id: int, match_id: int) -> bool:
        """Удалить уведомление"""
        try:
            key = f'notifications:{user_id}:{match_id}'
            
            if self.connected:
                self.redis_client.delete(key)
            else:
                self.local_cache.pop(key, None)
            
            logger.info(f"🗑️ Уведомление удалено")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении уведомления: {e}")
            return False
    
    # ============ ОБЩИЕ ОПЕРАЦИИ ============
    
    def clear_all(self) -> bool:
        """Очистить весь кэш"""
        try:
            if self.connected:
                self.redis_client.flushdb()
                logger.info("🧹 Redis кэш полностью очищен")
            else:
                self.local_cache.clear()
                logger.info("🧹 Локальный кэш полностью очищен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке кэша: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Получить статистику кэша"""
        try:
            if self.connected:
                info = self.redis_client.info('memory')
                return {
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'used_memory_peak': info.get('used_memory_peak_human', 'N/A'),
                    'connected': True,
                    'type': 'Redis'
                }
            else:
                return {
                    'items': len(self.local_cache),
                    'connected': False,
                    'type': 'Local'
                }
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {'error': str(e)}


# Глобальный экземпляр кэша
_cache = None

def get_cache() -> RedisCache:
    """Получить глобальный экземпляр кэша"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache

if __name__ == "__main__":
    # Тестирование кэша
    logging.basicConfig(level=logging.INFO)
    
    cache = get_cache()
    
    print("\n=== Тестирование Redis кэша ===\n")
    
    # Тест матчей
    print("1️⃣ Тест матчей:")
    test_matches = [
        {'id': 0, 'title': 'Матч 1', 'url': 'http://example.com/1'},
        {'id': 1, 'title': 'Матч 2', 'url': 'http://example.com/2'},
    ]
    cache.set_matches(test_matches)
    retrieved = cache.get_matches()
    print(f"✅ Матчи: {len(retrieved)} шт\n")
    
    # Тест избранных
    print("2️⃣ Тест избранных:")
    cache.add_favorite(123, 0)
    cache.add_favorite(123, 1)
    favorites = cache.get_favorites(123)
    print(f"✅ Избранные: {favorites}\n")
    
    # Тест уведомлений
    print("3️⃣ Тест уведомлений:")
    notify_time = int(time.time()) + 900  # 15 минут
    cache.add_notification(123, 0, 'Матч 1', notify_time)
    pending = cache.get_pending_notifications()
    print(f"✅ Ожидающих уведомлений: {len(pending)} шт\n")
    
    # Статистика
    print("4️⃣ Статистика:")
    stats = cache.get_stats()
    print(f"✅ {stats}\n")
