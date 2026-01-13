/**
 * API для взаимодействия между Web App и ботом
 * Получение данных о матчах и потоках через REST API
 */

export interface Match {
  id: number;
  title: string;
  url: string;
}

export interface Channel {
  id: number;
  title: string;
  url: string;
  type: 'web' | 'acestream';
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// API базовый URL - может быть переопределен через переменные окружения
const API_BASE_URL = process.env.VITE_API_URL || 'https://futlive-player-v2.manus.space/api';

// Максимальное количество попыток retry
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // мс

/**
 * Функция для retry с экспоненциальной задержкой
 */
async function fetchWithRetry(
  url: string,
  options?: RequestInit,
  retries = MAX_RETRIES
): Promise<Response> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok && response.status >= 500 && retries > 0) {
      // Retry на server errors
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (MAX_RETRIES - retries + 1)));
      return fetchWithRetry(url, options, retries - 1);
    }

    return response;
  } catch (error) {
    if (retries > 0) {
      // Retry на network errors
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (MAX_RETRIES - retries + 1)));
      return fetchWithRetry(url, options, retries - 1);
    }
    throw error;
  }
}

/**
 * Получить все доступные матчи
 */
export async function getMatches(): Promise<ApiResponse<Match[]>> {
  try {
    const response = await fetchWithRetry(`${API_BASE_URL}/matches`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      return {
        success: false,
        error: data.error || 'Ошибка при получении матчей',
      };
    }

    return {
      success: true,
      data: data.data || [],
    };
  } catch (error) {
    console.error('Error fetching matches:', error);
    return {
      success: false,
      error: `Ошибка при получении матчей: ${error}`,
    };
  }
}

/**
 * Получить матч по ID
 */
export async function getMatch(matchId: number): Promise<ApiResponse<Match>> {
  try {
    const response = await fetchWithRetry(`${API_BASE_URL}/match/${matchId}`);

    if (!response.ok) {
      if (response.status === 404) {
        return {
          success: false,
          error: 'Матч не найден',
        };
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      return {
        success: false,
        error: data.error || 'Не удалось получить матч',
      };
    }

    return {
      success: true,
      data: data.data,
    };
  } catch (error) {
    console.error(`Error fetching match ${matchId}:`, error);
    return {
      success: false,
      error: `Ошибка при получении матча: ${error}`,
    };
  }
}

/**
 * Получить все каналы для матча
 */
export async function getChannels(matchId: number): Promise<ApiResponse<Channel[]>> {
  try {
    const response = await fetchWithRetry(`${API_BASE_URL}/channels/${matchId}`);

    if (!response.ok) {
      if (response.status === 404) {
        return {
          success: false,
          error: 'Матч не найден',
        };
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      return {
        success: false,
        error: data.error || 'Не удалось получить каналы',
      };
    }

    return {
      success: true,
      data: data.data || [],
    };
  } catch (error) {
    console.error(`Error fetching channels for match ${matchId}:`, error);
    return {
      success: false,
      error: `Ошибка при получении каналов: ${error}`,
    };
  }
}

/**
 * Получить конкретный канал
 */
export async function getChannel(
  matchId: number,
  channelId: number
): Promise<ApiResponse<Channel>> {
  try {
    const response = await fetchWithRetry(`${API_BASE_URL}/channel/${matchId}/${channelId}`);

    if (!response.ok) {
      if (response.status === 404) {
        return {
          success: false,
          error: 'Канал не найден',
        };
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      return {
        success: false,
        error: data.error || 'Не удалось получить канал',
      };
    }

    return {
      success: true,
      data: data.data,
    };
  } catch (error) {
    console.error(`Error fetching channel ${matchId}/${channelId}:`, error);
    return {
      success: false,
      error: `Ошибка при получении канала: ${error}`,
    };
  }
}

/**
 * Получить URL потока для канала
 */
export async function getStreamUrl(
  matchId: number,
  channelId: number
): Promise<ApiResponse<string>> {
  try {
    const channel = await getChannel(matchId, channelId);

    if (!channel.success || !channel.data) {
      return {
        success: false,
        error: channel.error || 'Канал не найден',
      };
    }

    return {
      success: true,
      data: channel.data.url,
    };
  } catch (error) {
    console.error(`Error fetching stream URL ${matchId}/${channelId}:`, error);
    return {
      success: false,
      error: `Ошибка при получении URL потока: ${error}`,
    };
  }
}

/**
 * Очистить кэш матчей на сервере
 */
export async function clearCache(): Promise<ApiResponse<void>> {
  try {
    const response = await fetch(`${API_BASE_URL}/clear-cache`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    return {
      success: data.success,
      error: data.error,
    };
  } catch (error) {
    console.error('Error clearing cache:', error);
    return {
      success: false,
      error: `Ошибка при очистке кэша: ${error}`,
    };
  }
}

/**
 * Проверить здоровье API
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return response.ok;
  } catch (error) {
    console.error('API health check failed:', error);
    return false;
  }
}
