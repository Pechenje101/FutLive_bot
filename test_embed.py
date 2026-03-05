"""Тестирование извлечения embed URL"""
import asyncio
import sys
sys.path.insert(0, '/home/z/my-project/futlive-bot')

from match_finder import MatchFinder

async def test():
    finder = MatchFinder()
    
    # Получаем матчи
    print("🔍 Загрузка матчей...")
    matches = await finder.find_live_matches()
    
    if not matches:
        print("❌ Матчи не найдены")
        return
    
    # Тестируем первый матч
    match = matches[0]
    print(f"\n📋 Тест матча: {match['title']}")
    print(f"   URL: {match['url']}")
    
    # Получаем данные плеера
    print("\n🎥 Извлечение embed URL...")
    data = await finder.get_match_data(match['url'])
    
    print(f"\n📊 Результат:")
    print(f"   embed_url: {data.get('embed_url', 'НЕ НАЙДЕН')}")
    print(f"   acestreams: {len(data.get('acestreams', []))}")
    
    if data.get('acestreams'):
        for i, as_url in enumerate(data['acestreams'][:3]):
            print(f"      {i+1}. {as_url}")
    
    await finder.close_browser()

if __name__ == "__main__":
    asyncio.run(test())
