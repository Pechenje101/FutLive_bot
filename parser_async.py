#!/usr/bin/env python3
"""
Асинхронная обертка над парсером для использования в API сервере
Преобразует синхронные функции парсера в асинхронные
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from parser import GoooolParser

# Глобальный парсер
_parser = None
_executor = ThreadPoolExecutor(max_workers=3)

def get_parser():
    """Получить или создать экземпляр парсера"""
    global _parser
    if _parser is None:
        _parser = GoooolParser()
    return _parser

async def get_matches():
    """Асинхронно получить матчи"""
    loop = asyncio.get_event_loop()
    parser = get_parser()
    
    # Запускаем синхронную функцию в отдельном потоке
    matches = await loop.run_in_executor(
        _executor,
        parser.get_matches
    )
    
    return matches

async def get_match_links(match_url):
    """Асинхронно получить ссылки для матча"""
    loop = asyncio.get_event_loop()
    parser = get_parser()
    
    # Запускаем синхронную функцию в отдельном потоке
    links = await loop.run_in_executor(
        _executor,
        parser.get_links,
        match_url
    )
    
    # Преобразуем список ссылок в словарь для API
    links_dict = {}
    for i, link in enumerate(links):
        title = link.get('title', f'Channel {i+1}')
        url = link.get('url', '')
        if url:
            links_dict[title] = url
    
    return links_dict

async def test_parser():
    """Тестирование парсера"""
    print("🧪 Тестирование асинхронного парсера...")
    
    try:
        matches = await get_matches()
        print(f"✅ Найдено матчей: {len(matches)}")
        
        if matches:
            first_match = matches[0]
            print(f"📺 Первый матч: {first_match.get('title')}")
            
            links = await get_match_links(first_match.get('url'))
            print(f"✅ Найдено ссылок: {len(links)}")
            
            for title, url in list(links.items())[:3]:
                print(f"  - {title}: {url[:60]}...")
        else:
            print("⚠️ Матчи не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parser())
