#!/usr/bin/env python3
"""
Сервис уведомлений о матчах
Отправляет напоминания пользователям за 15 минут до начала матча
"""

import asyncio
import logging
import time
from typing import Optional, Callable
from datetime import datetime, timedelta
from redis_cache import get_cache

logger = logging.getLogger(__name__)

class NotificationService:
    """Сервис для управления уведомлениями о матчах"""
    
    def __init__(self, check_interval: int = 60, notify_before_minutes: int = 15):
        """
        Инициализация сервиса уведомлений
        
        Args:
            check_interval: Интервал проверки уведомлений в секундах
            notify_before_minutes: За сколько минут до матча отправлять уведомление
        """
        self.cache = get_cache()
        self.check_interval = check_interval
        self.notify_before_minutes = notify_before_minutes
        self.notify_before_seconds = notify_before_minutes * 60
        self.running = False
        self.on_notification_callback: Optional[Callable] = None
    
    def set_notification_callback(self, callback: Callable):
        """
        Установить callback для отправки уведомлений
        
        Args:
            callback: Асинхронная функция(notification_dict) для отправки уведомления
        """
        self.on_notification_callback = callback
        logger.info(f"📞 Callback для уведомлений установлен")
    
    def add_match_reminder(self, user_id: int, match_id: int, match_title: str, 
                          match_start_time: int) -> bool:
        """
        Добавить напоминание о матче
        
        Args:
            user_id: ID пользователя Telegram
            match_id: ID матча
            match_title: Название матча
            match_start_time: Unix timestamp начала матча
        
        Returns:
            True если успешно
        """
        try:
            # Вычисляем время отправки уведомления (за 15 минут до начала)
            notify_time = match_start_time - self.notify_before_seconds
            
            # Если время уведомления уже прошло, не добавляем
            current_time = int(time.time())
            if notify_time < current_time:
                logger.warning(f"⚠️ Время уведомления уже прошло для матча {match_id}")
                return False
            
            # Сохраняем в кэш
            self.cache.add_notification(user_id, match_id, match_title, notify_time)
            
            time_until = notify_time - current_time
            logger.info(f"⏰ Напоминание добавлено: матч '{match_title}' через {time_until}с")
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении напоминания: {e}")
            return False
    
    def remove_match_reminder(self, user_id: int, match_id: int) -> bool:
        """Удалить напоминание о матче"""
        try:
            self.cache.delete_notification(user_id, match_id)
            logger.info(f"🗑️ Напоминание удалено для пользователя {user_id}, матч {match_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении напоминания: {e}")
            return False
    
    async def check_and_send_notifications(self) -> int:
        """
        Проверить и отправить ожидающие уведомления
        
        Returns:
            Количество отправленных уведомлений
        """
        try:
            current_time = int(time.time())
            pending_notifications = self.cache.get_pending_notifications(current_time)
            
            sent_count = 0
            
            for notification in pending_notifications:
                try:
                    # Отправляем уведомление через callback
                    if self.on_notification_callback:
                        await self.on_notification_callback(notification)
                    
                    # Отмечаем как отправленное
                    self.cache.mark_notification_sent(
                        notification['user_id'],
                        notification['match_id']
                    )
                    
                    sent_count += 1
                    logger.info(f"✅ Уведомление отправлено пользователю {notification['user_id']}")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке уведомления: {e}")
            
            if sent_count > 0:
                logger.info(f"📬 Отправлено {sent_count} уведомлений")
            
            return sent_count
        
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке уведомлений: {e}")
            return 0
    
    async def start(self):
        """Запустить сервис уведомлений"""
        self.running = True
        logger.info(f"🚀 Сервис уведомлений запущен (интервал проверки: {self.check_interval}s)")
        
        try:
            while self.running:
                try:
                    # Проверяем и отправляем уведомления
                    await self.check_and_send_notifications()
                    
                    # Ждем перед следующей проверкой
                    await asyncio.sleep(self.check_interval)
                
                except Exception as e:
                    logger.error(f"❌ Ошибка в цикле проверки: {e}")
                    await asyncio.sleep(self.check_interval)
        
        except asyncio.CancelledError:
            logger.info("⏹️ Сервис уведомлений остановлен")
            self.running = False
    
    def stop(self):
        """Остановить сервис уведомлений"""
        self.running = False
        logger.info("⏹️ Остановка сервиса уведомлений...")


# Глобальный экземпляр сервиса
_notification_service = None

def get_notification_service() -> NotificationService:
    """Получить глобальный экземпляр сервиса уведомлений"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


async def test_notifications():
    """Тестирование сервиса уведомлений"""
    logging.basicConfig(level=logging.INFO)
    
    service = get_notification_service()
    
    # Устанавливаем callback для тестирования
    async def test_callback(notification):
        print(f"\n📬 УВЕДОМЛЕНИЕ:")
        print(f"   Пользователь: {notification['user_id']}")
        print(f"   Матч: {notification['match_title']}")
        print(f"   Время отправки: {datetime.fromtimestamp(notification['notify_time'])}")
    
    service.set_notification_callback(test_callback)
    
    print("\n=== Тестирование сервиса уведомлений ===\n")
    
    # Добавляем тестовое напоминание на 5 секунд в будущем
    current_time = int(time.time())
    match_start_time = current_time + 5 + (15 * 60)  # Матч через 5 + 15 минут
    
    print(f"1️⃣ Добавляем напоминание на {datetime.fromtimestamp(match_start_time)}")
    service.add_match_reminder(
        user_id=123,
        match_id=0,
        match_title="Тестовый матч",
        match_start_time=match_start_time
    )
    
    print(f"2️⃣ Запускаем сервис (будет проверять каждые 1 сек)...")
    
    # Запускаем сервис с коротким интервалом для тестирования
    service.check_interval = 1
    
    # Запускаем в отдельной задаче
    task = asyncio.create_task(service.start())
    
    # Ждем 10 секунд
    try:
        await asyncio.sleep(10)
    finally:
        service.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    print("\n✅ Тестирование завершено\n")


if __name__ == "__main__":
    asyncio.run(test_notifications())
