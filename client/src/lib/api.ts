/**
 * API для взаимодействия между Web App и ботом
 * Получение данных о матчах и потоках
 */

export interface Match {
  title: string;
  url: string;
  channels: Channel[];
}

export interface Channel {
  title: string;
  url: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Mock API для тестирования (когда парсер недоступен)
 */
const MOCK_MATCHES: Match[] = [
  {
    title: "Эвертон - Сандерленд",
    url: "https://gooool365.org/online/191987-jeverton-sanderlend-10-janvarja-prjamaja-transljacija.html",
    channels: [
      { title: "Setanta Sports 1 HD", url: "acestream://c58ddd8c6bb963fa78e6f79d2e3c6a15d93f8241" },
      { title: "DAZN 2 HD", url: "acestream://12ea555dd31dbe51fc8e4ca745aec09fe22a4865" },
      { title: "SPORT TV 1 HD", url: "acestream://af3e4e9fcc5a69848b7f8dd3fcf2cdde72bf1b4b" },
    ]
  },
  {
    title: "Манчестер Сити - Челси",
    url: "https://gooool365.org/online/test-match-2.html",
    channels: [
      { title: "Sky Sports 1", url: "https://example.com/stream1" },
      { title: "BT Sport", url: "https://example.com/stream2" },
    ]
  },
  {
    title: "Ливерпуль - Арсенал",
    url: "https://gooool365.org/online/test-match-3.html",
    channels: [
      { title: "Premier League HD", url: "acestream://abc123def456ghi789jkl012mno345pqr678stu" },
      { title: "Матч ТВ", url: "https://example.com/stream3" },
    ]
  },
];

/**
 * Получить все доступные матчи
 */
export async function getMatches(): Promise<ApiResponse<Match[]>> {
  try {
    // В production это будет запрос к API бота
    // const response = await fetch('/api/matches');
    // return response.json();
    
    // Для тестирования используем mock данные
    await new Promise(resolve => setTimeout(resolve, 500)); // Имитируем задержку сети
    
    return {
      success: true,
      data: MOCK_MATCHES,
    };
  } catch (error) {
    return {
      success: false,
      error: `Ошибка при получении матчей: ${error}`,
    };
  }
}

/**
 * Получить матч по индексу
 */
export async function getMatch(matchId: number): Promise<ApiResponse<Match>> {
  try {
    const matches = await getMatches();
    
    if (!matches.success || !matches.data) {
      return {
        success: false,
        error: "Не удалось получить матчи",
      };
    }
    
    if (matchId < 0 || matchId >= matches.data.length) {
      return {
        success: false,
        error: "Матч не найден",
      };
    }
    
    return {
      success: true,
      data: matches.data[matchId],
    };
  } catch (error) {
    return {
      success: false,
      error: `Ошибка при получении матча: ${error}`,
    };
  }
}

/**
 * Получить канал по индексу матча и канала
 */
export async function getChannel(
  matchId: number,
  channelId: number
): Promise<ApiResponse<Channel>> {
  try {
    const match = await getMatch(matchId);
    
    if (!match.success || !match.data) {
      return {
        success: false,
        error: "Матч не найден",
      };
    }
    
    if (channelId < 0 || channelId >= match.data.channels.length) {
      return {
        success: false,
        error: "Канал не найден",
      };
    }
    
    return {
      success: true,
      data: match.data.channels[channelId],
    };
  } catch (error) {
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
        error: "Канал не найден",
      };
    }
    
    return {
      success: true,
      data: channel.data.url,
    };
  } catch (error) {
    return {
      success: false,
      error: `Ошибка при получении URL потока: ${error}`,
    };
  }
}

/**
 * Получить все каналы для матча
 */
export async function getChannels(matchId: number): Promise<ApiResponse<Channel[]>> {
  try {
    const match = await getMatch(matchId);
    
    if (!match.success || !match.data) {
      return {
        success: false,
        error: "Матч не найден",
      };
    }
    
    return {
      success: true,
      data: match.data.channels,
    };
  } catch (error) {
    return {
      success: false,
      error: `Ошибка при получении каналов: ${error}`,
    };
  }
}
