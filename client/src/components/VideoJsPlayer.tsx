import { useEffect, useRef, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

interface VideoJsPlayerProps {
  url: string;
  title?: string;
  onError?: (error: string) => void;
}

// Конфигурация retry
const RETRY_CONFIG = {
  maxAttempts: 3,
  delayMs: 2000,
  backoffMultiplier: 1.5,
};

// Список Ace Stream прокси для fallback
const ACE_STREAM_PROXIES = [
  'https://ace.as-proxy.com/play',
  'https://acestream.proxy.manus.space/play',
  'https://aceplay.net/play',
];

export default function VideoJsPlayer({ url, title, onError }: VideoJsPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [proxyIndex, setProxyIndex] = useState(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  /**
   * Получить URL для Ace Stream с использованием прокси
   */
  const getAceStreamUrl = (aceId: string, proxyIdx: number = 0): string => {
    const proxy = ACE_STREAM_PROXIES[proxyIdx % ACE_STREAM_PROXIES.length];
    return `${proxy}?id=${aceId}`;
  };

  /**
   * Обработка ошибки плеера с retry логикой
   */
  const handlePlayerError = (errorMessage: string) => {
    console.error('Player error:', errorMessage);
    setError(errorMessage);
    onError?.(errorMessage);
    setIsLoading(false);

    // Если это Ace Stream, пробуем следующий прокси
    if (url.startsWith('acestream://') && proxyIndex < ACE_STREAM_PROXIES.length - 1) {
      console.log(`Trying next Ace Stream proxy (${proxyIndex + 1}/${ACE_STREAM_PROXIES.length})`);
      
      retryTimeoutRef.current = setTimeout(() => {
        setProxyIndex((prev: number) => prev + 1);
        setError(null);
        setIsLoading(true);
        setRetryCount(0);
      }, RETRY_CONFIG.delayMs);
      
      return;
    }

    // Если это не Ace Stream или исчерпаны прокси, используем обычную retry логику
    if (retryCount < RETRY_CONFIG.maxAttempts) {
      const delayMs = RETRY_CONFIG.delayMs * Math.pow(RETRY_CONFIG.backoffMultiplier, retryCount);
      console.log(`Retrying in ${delayMs}ms (attempt ${retryCount + 1}/${RETRY_CONFIG.maxAttempts})`);
      
      retryTimeoutRef.current = setTimeout(() => {
        setRetryCount((prev: number) => prev + 1);
        setError(null);
        setIsLoading(true);
      }, delayMs);
    }
  };

  useEffect(() => {
    if (!videoRef.current) return;

    // Инициализация Video.js плеера
    const player = videojs(videoRef.current, {
      controls: true,
      autoplay: true,
      preload: 'auto',
      responsive: true,
      fluid: true,
      playbackRates: [0.5, 1, 1.5, 2],
      controlBar: {
        children: [
          'playToggle',
          'volumePanel',
          'currentTimeDisplay',
          'timeDivider',
          'durationDisplay',
          'progressControl',
          'playbackRateMenuButton',
          'fullscreenToggle',
        ],
      },
    });

    playerRef.current = player;

    // Обработка ошибок плеера
    const handleError = () => {
      const errorObj = player.error();
      const errorCode = errorObj?.code;
      const errorMessage = errorObj?.message || 'Неизвестная ошибка';
      
      // Маппинг кодов ошибок Video.js
      const errorMessages: { [key: number]: string } = {
        1: 'MEDIA_ERR_ABORTED - Загрузка отменена',
        2: 'MEDIA_ERR_NETWORK - Ошибка сети',
        3: 'MEDIA_ERR_DECODE - Ошибка декодирования',
        4: 'MEDIA_ERR_SRC_NOT_SUPPORTED - Источник не поддерживается',
      };

      const message = errorMessages[errorCode as number] || `Ошибка плеера (${errorCode}): ${errorMessage}`;
      handlePlayerError(message);
    };

    player.on('error', handleError);

    // Обработка загрузки
    player.on('loadstart', () => {
      setIsLoading(true);
      setError(null);
    });

    player.on('canplay', () => {
      setIsLoading(false);
      setRetryCount(0); // Сброс счетчика при успешной загрузке
    });

    player.on('play', () => {
      setIsLoading(false);
    });

    // Обработка timeout для долгой загрузки
    const loadTimeout = setTimeout(() => {
      if (isLoading && playerRef.current) {
        handlePlayerError('Timeout: Потоку требуется слишком много времени для загрузки');
      }
    }, 30000); // 30 секунд

    // Обновление источника видео
    if (url) {
      try {
        let sourceType = 'application/x-mpegURL'; // По умолчанию HLS
        let sourceUrl = url;

        if (url.includes('.mp4')) {
          sourceType = 'video/mp4';
        } else if (url.includes('.m3u8')) {
          sourceType = 'application/x-mpegURL';
        } else if (url.includes('.mpd')) {
          sourceType = 'application/dash+xml';
        } else if (url.startsWith('acestream://')) {
          // Для Ace Stream используем прокси с fallback
          const aceId = url.replace('acestream://', '');
          sourceUrl = getAceStreamUrl(aceId, proxyIndex);
          sourceType = 'video/mp4';
          console.log(`Loading Ace Stream with proxy ${proxyIndex}: ${sourceUrl}`);
        }

        player.src({ src: sourceUrl, type: sourceType });
      } catch (err) {
        handlePlayerError(`Ошибка при загрузке источника: ${err}`);
      }
    }

    // Cleanup
    return () => {
      clearTimeout(loadTimeout);
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [url, onError, retryCount, proxyIndex]);

  return (
    <div className="w-full h-full bg-black rounded-lg overflow-hidden">
      <div className="relative w-full h-full">
        <video
          ref={videoRef}
          className="video-js vjs-default-skin w-full h-full"
          data-setup="{}"
        />

        {/* Индикатор загрузки */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 border-4 border-gray-600 border-t-white rounded-full animate-spin" />
              <p className="text-white text-sm">{title || 'Загрузка...'}</p>
              {retryCount > 0 && (
                <p className="text-gray-400 text-xs">
                  Попытка {retryCount}/{RETRY_CONFIG.maxAttempts}
                </p>
              )}
              {url.startsWith('acestream://') && proxyIndex > 0 && (
                <p className="text-gray-400 text-xs">
                  Прокси {proxyIndex + 1}/{ACE_STREAM_PROXIES.length}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Сообщение об ошибке */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-center px-4">
              <div className="text-red-500 text-4xl">⚠️</div>
              <p className="text-white text-sm font-medium">{error}</p>
              <p className="text-gray-400 text-xs">
                {retryCount < RETRY_CONFIG.maxAttempts
                  ? `Автоматическая повторная попытка...`
                  : 'Попробуйте выбрать другой канал'}
              </p>
              {url.startsWith('acestream://') && proxyIndex < ACE_STREAM_PROXIES.length - 1 && (
                <p className="text-gray-400 text-xs">
                  Пробуем другой прокси...
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
