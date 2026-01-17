"""
Конфигурация Sentry для мониторинга ошибок в Backend
"""

import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

def init_sentry():
    """Инициализация Sentry для отслеживания ошибок"""
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        print("⚠️ SENTRY_DSN не установлен, мониторинг отключен")
        return
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,  # 10% транзакций для трассировки
        environment=os.getenv('FLASK_ENV', 'production'),
        release=os.getenv('APP_VERSION', '1.0.0'),
        debug=False
    )
    
    print("✅ Sentry инициализирован")

def capture_exception(exception, context=None):
    """Отправить исключение в Sentry"""
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_exception(exception)

def capture_message(message, level='info'):
    """Отправить сообщение в Sentry"""
    sentry_sdk.capture_message(message, level=level)
