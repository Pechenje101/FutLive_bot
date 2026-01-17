"""
API сервер для Web App плеера
Предоставляет данные о матчах и каналах через REST API
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import asyncio
import sys
import time
import os
sys.path.insert(0, '/home/ubuntu/futlive-player-v2')

from parser_async import get_matches, get_match_links
from sentry_config import init_sentry, capture_exception
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
CORS(app)

# Инициализация Sentry
init_sentry()

# Инициализация Prometheus метрик
metrics = PrometheusMetrics(app)
metrics.info('futlive_app_info', 'FutLive Player API', version='1.0.0')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Кэш данных
matches_cache = {}
cache_timestamp = 0
CACHE_DURATION = 300  # 5 минут

def get_cached_matches():
    """Получить матчи с кэшированием"""
    global matches_cache, cache_timestamp
    
    current_time = time.time()
    if matches_cache and (current_time - cache_timestamp) < CACHE_DURATION:
        logger.info(f"📦 Возвращаем кэшированные матчи ({len(matches_cache)} шт)")
        return matches_cache
    
    try:
        logger.info("🔄 Загрузка матчей из парсера...")
        
        # Создаем новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            matches = loop.run_until_complete(get_matches())
        finally:
            loop.close()
        
        matches_cache = matches
        cache_timestamp = current_time
        logger.info(f"✅ Загружено {len(matches)} матчей")
        return matches
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке матчей: {e}")
        capture_exception(e, {'context': 'get_cached_matches'})
        return []

@app.route('/api/health', methods=['GET'])
def health():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'OK',
        'success': True,
        'version': '1.0.0'
    })

@app.route('/api/matches', methods=['GET'])
def api_matches():
    """Получить все матчи"""
    try:
        logger.info("📺 Запрос: GET /api/matches")
        matches = get_cached_matches()
        
        # Преобразуем в формат для API
        result = []
        for idx, match in enumerate(matches):
            result.append({
                'id': idx,
                'title': match.get('title', 'Unknown'),
                'url': match.get('url', ''),
            })
        
        logger.info(f"✅ Возвращаем {len(result)} матчей")
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/matches: {e}")
        capture_exception(e, {'context': 'api_matches'})
        return jsonify({
            'success': False,
            'error': 'Failed to fetch matches',
            'data': [],
            'count': 0
        }), 500

@app.route('/api/match/<int:match_id>', methods=['GET'])
def api_get_match(match_id):
    """Получить матч по ID (для Frontend)"""
    try:
        logger.info(f"📺 Запрос: GET /api/match/{match_id}")
        matches = get_cached_matches()
        
        if match_id >= len(matches):
            return jsonify({
                'success': False,
                'error': 'Match not found',
                'data': None
            }), 404
        
        match = matches[match_id]
        result = {
            'id': match_id,
            'title': match.get('title', 'Unknown'),
            'url': match.get('url', ''),
        }
        
        logger.info(f"✅ Возвращаем матч {match_id}")
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/match/{match_id}: {e}")
        capture_exception(e, {'context': f'api_get_match_{match_id}'})
        return jsonify({
            'success': False,
            'error': 'Failed to fetch match',
            'data': None
        }), 500

@app.route('/api/channels/<int:match_id>', methods=['GET'])
def api_get_channels(match_id):
    """Получить каналы для конкретного матча (для Frontend)"""
    try:
        logger.info(f"🔗 Запрос: GET /api/channels/{match_id}")
        matches = get_cached_matches()
        
        if match_id >= len(matches):
            return jsonify({
                'success': False,
                'error': 'Match not found',
                'data': []
            }), 404
        
        match = matches[match_id]
        match_url = match.get('url', '')
        
        # Получаем каналы для матча
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            links = loop.run_until_complete(get_match_links(match_url))
        finally:
            loop.close()
        
        # Преобразуем в формат для Frontend
        channels = []
        for idx, link in enumerate(links):
            channels.append({
                'id': idx,
                'title': link.get('title', f'Канал {idx + 1}'),
                'url': link.get('url', ''),
                'type': 'acestream' if link.get('url', '').startswith('acestream://') else 'web'
            })
        
        logger.info(f"✅ Найдено {len(channels)} каналов для матча {match_id}")
        return jsonify({
            'success': True,
            'data': channels
        })
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/channels/{match_id}: {e}")
        capture_exception(e, {'context': f'api_get_channels_{match_id}'})
        return jsonify({
            'success': False,
            'error': 'Failed to fetch channels',
            'data': []
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок"""
    return jsonify({
        'success': False,
        'error': 'Not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибок"""
    logger.error(f"❌ Internal server error: {error}")
    capture_exception(error)
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    logger.info("🚀 Запуск API сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)
