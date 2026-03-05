"""
Enhanced Bot with Multi-Source Support
"""

# Добавить в bot_final.py:

SOURCES = {
    'livetv': {
        'name': 'LiveTV',
        'emoji': '🌐',
        'priority': 1,
    },
    'cricfree': {
        'name': 'Cricfree', 
        'emoji': '📺',
        'priority': 2,
    },
    'sportrar': {
        'name': 'SportRAR',
        'emoji': '📡',
        'priority': 3,
    },
    'acestream': {
        'name': 'Ace Stream',
        'emoji': '🚀',
        'priority': 4,
    }
}

def get_source_keyboard(match: dict):
    """Клавиатура с выбором источника"""
    buttons = []
    
    # Основной источник
    buttons.append([
        InlineKeyboardButton(
            text=f"📺 Смотреть ({match.get('source', 'LiveTV')})",
            web_app=WebAppInfo(url=get_web_app_url(match))
        )
    ])
    
    # Альтернативные источники
    if match.get('acestreams'):
        buttons.append([
            InlineKeyboardButton(
                text="🚀 Ace Stream",
                callback_data=f"ace_{match['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="🌐 Открыть сайт",
            url=match['url']
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
