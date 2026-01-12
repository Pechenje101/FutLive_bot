import { useEffect, useRef, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

interface VideoJsPlayerProps {
  url: string;
  title?: string;
  onError?: (error: string) => void;
}

export default function VideoJsPlayer({ url, title, onError }: VideoJsPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

    // Обработка ошибок
    player.on('error', () => {
      const errorCode = player.error()?.code;
      const errorMessage = player.error()?.message || 'Неизвестная ошибка';
      const message = `Ошибка плеера (${errorCode}): ${errorMessage}`;
      setError(message);
      onError?.(message);
      setIsLoading(false);
    });

    // Обработка загрузки
    player.on('loadstart', () => {
      setIsLoading(true);
      setError(null);
    });

    player.on('canplay', () => {
      setIsLoading(false);
    });

    player.on('play', () => {
      setIsLoading(false);
    });

    // Обновление источника видео
    if (url) {
      // Определяем тип источника
      let sourceType = 'application/x-mpegURL'; // По умолчанию HLS
      
      if (url.includes('.mp4')) {
        sourceType = 'video/mp4';
      } else if (url.includes('.m3u8')) {
        sourceType = 'application/x-mpegURL';
      } else if (url.includes('.mpd')) {
        sourceType = 'application/dash+xml';
      } else if (url.startsWith('acestream://')) {
        // Для Ace Stream используем прокси
        const aceId = url.replace('acestream://', '');
        const proxyUrl = `https://ace.as-proxy.com/play?id=${aceId}`;
        player.src({ src: proxyUrl, type: 'video/mp4' });
        return;
      }

      player.src({ src: url, type: sourceType });
    }

    // Cleanup
    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [url, onError]);

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
            </div>
          </div>
        )}

        {/* Сообщение об ошибке */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-center px-4">
              <div className="text-red-500 text-4xl">⚠️</div>
              <p className="text-white text-sm font-medium">{error}</p>
              <p className="text-gray-400 text-xs">Попробуйте выбрать другой канал</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
