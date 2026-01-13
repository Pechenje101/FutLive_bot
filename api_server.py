#!/usr/bin/env python3
"""
API сервер для Web App плеера
Предоставляет данные о матчах и каналах через REST API
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import asyncio
import sys
sys.path.insert(0, '/home/ubuntu')

from parser import get_matches, get_match_links

app = Flask(__name__)
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Кэш данных
matches_cache = {}
cache_timestamp = 0
CACHE_DURATION = 300  # 5 минут

def get_cached_matches():
    """Получить матчи с кэшированием"""
    global matches_cache, cache_timestamp
    import time
    
    current_time = time.time()
    if matches_cache and (current_time - cache_timestamp) < CACHE_DURATION:
        return matches_cache
    
    try:
        # Получаем матчи синхронно из асинхронной функции
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        matches = loop.run_until_complete(get_matches())
        loop.close()
        
        matches_cache = matches
        cache_timestamp = current_time
        return matches
    except Exception as e:
        logger.error(f"Ошибка при получении матчей: {e}")
        return []

@app.route('/api/matches', methods=['GET'])
def api_matches():
    """Получить все матчи"""
    try:
        matches = get_cached_matches()
        
        # Преобразуем в формат для API
        result = []
        for idx, match in enumerate(matches):
            result.append({
                'id': idx,
                'title': match.get('title', 'Unknown'),
                'url': match.get('url', ''),
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
    except Exception as e:
        logger.error(f"Ошибка в /api/matches: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/match/<int:match_id>', methods=['GET'])
def api_match(match_id):
    """Получить информацию о конкретном матче"""
    try:
        matches = get_cached_matches()
        
        if match_id >= len(matches):
            return jsonify({
                'success': False,
                'error': 'Match not found'
            }), 404
        
        match = matches[match_id]
        
        return jsonify({
            'success': True,
            'data': {
                'id': match_id,
                'title': match.get('title', 'Unknown'),
                'url': match.get('url', ''),
            }
        })
    except Exception as e:
        logger.error(f"Ошибка в /api/match/{match_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/channels/<int:match_id>', methods=['GET'])
def api_channels(match_id):
    """Получить каналы для матча"""
    try:
        matches = get_cached_matches()
        
        if match_id >= len(matches):
            return jsonify({
                'success': False,
                'error': 'Match not found'
            }), 404
        
        match = matches[match_id]
        match_url = match.get('url', '')
        
        if not match_url:
            return jsonify({
                'success': False,
                'error': 'Match URL not found'
            }), 400
        
        # Получаем ссылки на каналы синхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        links = loop.run_until_complete(get_match_links(match_url))
        loop.close()
        
        # Преобразуем в формат для API
        channels = []
        for idx, (channel_name, channel_url) in enumerate(links.items()):
            channels.append({
                'id': idx,
                'title': channel_name,
                'url': channel_url,
                'type': 'acestream' if channel_url.startswith('acestream://') else 'web'
            })
        
        return jsonify({
            'success': True,
            'data': channels,
            'count': len(channels)
        })
    except Exception as e:
        logger.error(f"Ошибка в /api/channels/{match_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/channel/<int:match_id>/<int:channel_id>', methods=['GET'])
def api_channel(match_id, channel_id):
    """Получить конкретный канал"""
    try:
        matches = get_cached_matches()
        
        if match_id >= len(matches):
            return jsonify({
                'success': False,
                'error': 'Match not found'
            }), 404
        
        match = matches[match_id]
        match_url = match.get('url', '')
        
        # Получаем ссылки на каналы синхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        links = loop.run_until_complete(get_match_links(match_url))
        loop.close()
        
        channels = list(links.items())
        
        if channel_id >= len(channels):
            return jsonify({
                'success': False,
                'error': 'Channel not found'
            }), 404
        
        channel_name, channel_url = channels[channel_id]
        
        return jsonify({
            'success': True,
            'data': {
                'id': channel_id,
                'title': channel_name,
                'url': channel_url,
                'type': 'acestream' if channel_url.startswith('acestream://') else 'web'
            }
        })
    except Exception as e:
        logger.error(f"Ошибка в /api/channel/{match_id}/{channel_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Проверка здоровья API"""
    return jsonify({
        'success': True,
        'status': 'OK',
        'version': '1.0.0'
    })

@app.route('/api/clear-cache', methods=['POST'])
def api_clear_cache():
    """Очистить кэш матчей"""
    global matches_cache, cache_timestamp
    matches_cache = {}
    cache_timestamp = 0
    
    return jsonify({
        'success': True,
        'message': 'Cache cleared'
    })

@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибок"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    logger.info("🚀 API сервер запущен на http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
