/**
 * Утилиты для работы с Ace Stream ссылками и прокси
 */

/**
 * Список доступных Ace Stream прокси-сервисов
 * Каждый прокси имеет базовый URL и поддерживаемый формат параметров
 */
export const ACE_STREAM_PROXIES = [
  {
    name: 'ace.as-proxy.com',
    url: 'https://ace.as-proxy.com/play',
    format: 'id', // Параметр: ?id=XXXX
    priority: 1,
  },
  {
    name: 'acestream.proxy.manus.space',
    url: 'https://acestream.proxy.manus.space/play',
    format: 'id',
    priority: 2,
  },
  {
    name: 'aceplay.net',
    url: 'https://aceplay.net/play',
    format: 'id',
    priority: 3,
  },
  {
    name: 'acestream.online',
    url: 'https://acestream.online/play',
    format: 'id',
    priority: 4,
  },
];

/**
 * Извлечь ID из acestream:// ссылки
 */
export function extractAceStreamId(url: string): string | null {
  if (!url.startsWith('acestream://')) {
    return null;
  }
  return url.replace('acestream://', '').split('?')[0];
}

/**
 * Проверить, является ли URL acestream ссылкой
 */
export function isAceStreamUrl(url: string): boolean {
  return url.startsWith('acestream://');
}

/**
 * Получить HTTP URL для Ace Stream через прокси
 */
export function getAceStreamProxyUrl(aceId: string, proxyIndex: number = 0): string {
  const proxy = ACE_STREAM_PROXIES[proxyIndex % ACE_STREAM_PROXIES.length];
  return `${proxy.url}?${proxy.format}=${aceId}`;
}

/**
 * Получить следующий прокси для fallback
 */
export function getNextAceStreamProxy(currentIndex: number): number {
  return (currentIndex + 1) % ACE_STREAM_PROXIES.length;
}

/**
 * Проверить, есть ли еще доступные прокси
 */
export function hasMoreProxies(currentIndex: number): boolean {
  return currentIndex < ACE_STREAM_PROXIES.length - 1;
}

/**
 * Получить информацию о прокси
 */
export function getProxyInfo(proxyIndex: number) {
  return ACE_STREAM_PROXIES[proxyIndex % ACE_STREAM_PROXIES.length];
}

/**
 * Сортировать прокси по приоритету
 */
export function getSortedProxies() {
  return [...ACE_STREAM_PROXIES].sort((a, b) => a.priority - b.priority);
}

/**
 * Попытаться загрузить Ace Stream через различные прокси
 */
export async function tryLoadAceStream(
  aceId: string,
  onProxyChange?: (proxyIndex: number, proxyName: string) => void
): Promise<string | null> {
  for (let i = 0; i < ACE_STREAM_PROXIES.length; i++) {
    const proxyUrl = getAceStreamProxyUrl(aceId, i);
    const proxyInfo = getProxyInfo(i);

    onProxyChange?.(i, proxyInfo.name);

    try {
      // Проверяем доступность прокси с HEAD запросом
      const response = await fetch(proxyUrl, {
        method: 'HEAD',
        mode: 'no-cors',
      });

      if (response.ok || response.status === 0) {
        // Прокси доступен
        return proxyUrl;
      }
    } catch (error) {
      console.warn(`Proxy ${proxyInfo.name} failed:`, error);
      continue;
    }
  }

  return null;
}

/**
 * Конвертировать acestream:// ссылку в HTTP URL
 */
export function convertAceStreamToHttp(url: string, proxyIndex: number = 0): string | null {
  const aceId = extractAceStreamId(url);
  if (!aceId) {
    return null;
  }
  return getAceStreamProxyUrl(aceId, proxyIndex);
}

/**
 * Получить рекомендуемый прокси на основе региона (если доступно)
 */
export function getRecommendedProxy(): number {
  // По умолчанию используем первый прокси с наивысшим приоритетом
  return 0;
}
