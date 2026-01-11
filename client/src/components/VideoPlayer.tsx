import { useState, useEffect, useRef } from 'react';
import { AlertCircle, Loader, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface VideoPlayerProps {
  url: string;
  title?: string;
  onError?: (error: string) => void;
  onLoading?: (isLoading: boolean) => void;
}

export default function VideoPlayer({ url, title, onError, onLoading }: VideoPlayerProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryCount, setRetryCount] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const MAX_RETRIES = 3;
  const LOAD_TIMEOUT = 15000; // 15 секунд

  useEffect(() => {
    if (!url) {
      setError('Ссылка не предоставлена');
      setIsLoading(false);
      return;
    }

    loadPlayer();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [url]);

  useEffect(() => {
    onLoading?.(isLoading);
  }, [isLoading, onLoading]);

  useEffect(() => {
    if (error) {
      onError?.(error);
    }
  }, [error, onError]);

  const loadPlayer = (): void => {
    setIsLoading(true);
    setError('');

    // Определяем тип контента
    if (url.startsWith('acestream://')) {
      handleAceStream();
    } else if (url.startsWith('http')) {
      handleHttpStream();
    } else {
      setError('Неподдерживаемый формат ссылки');
      setIsLoading(false);
    }

    // Таймер загрузки
    timeoutRef.current = setTimeout(() => {
      if (isLoading) {
        setError('Время загрузки истекло. Попробуйте другой канал.');
        setIsLoading(false);
      }
    }, LOAD_TIMEOUT);
  };

  const handleAceStream = (): void => {
    // Для Ace Stream показываем информацию о необходимости установки приложения
    setIsLoading(false);
    setError('acestream'); // Специальный флаг для отображения информации об Ace Stream
  };

  const handleHttpStream = (): void => {
    // Пробуем загрузить как iframe
    if (iframeRef.current) {
      iframeRef.current.src = url;
    }
  };

  const handleIframeLoad = (): void => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsLoading(false);
  };

  const handleIframeError = (): void => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (retryCount < MAX_RETRIES) {
      setRetryCount(retryCount + 1);
      setTimeout(() => {
        loadPlayer();
      }, 2000);
    } else {
      setError('Не удалось загрузить видео. Попробуйте другой канал.');
      setIsLoading(false);
    }
  };

  const handleRetry = (): void => {
    setRetryCount(0);
    loadPlayer();
  };

  if (error === 'acestream') {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black">
        <div className="text-center text-white max-w-sm">
          <div className="text-5xl mb-4">🌀</div>
          <h3 className="text-xl font-semibold mb-2">Ace Stream</h3>
          <p className="text-white/70 text-sm mb-4">
            Установите приложение Ace Stream Media для просмотра этого канала
          </p>
          <code className="bg-slate-800 text-blue-400 text-xs p-3 rounded block mb-4 break-all">
            {url.replace('acestream://', '')}
          </code>
          <Button
            onClick={() => navigator.clipboard.writeText(url.replace('acestream://', ''))}
            className="w-full"
            variant="default"
          >
            📋 Копировать ID
          </Button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black">
        <div className="text-center text-white max-w-sm">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Ошибка загрузки</h3>
          <p className="text-white/70 text-sm mb-4">{error}</p>
          {retryCount < MAX_RETRIES && (
            <p className="text-white/50 text-xs mb-4">
              Попытка {retryCount + 1} из {MAX_RETRIES}
            </p>
          )}
          <Button
            onClick={handleRetry}
            className="w-full"
            variant="default"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Попробовать снова
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full bg-black relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
          <div className="text-center">
            <Loader className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
            <p className="text-white text-sm">Загрузка видео...</p>
            {retryCount > 0 && (
              <p className="text-white/60 text-xs mt-2">
                Попытка {retryCount + 1} из {MAX_RETRIES}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Iframe плеер */}
      <iframe
        ref={iframeRef}
        className="w-full h-full border-none"
        allowFullScreen
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
        referrerPolicy="no-referrer"
        sandbox="allow-forms allow-modals allow-orientation-lock allow-pointer-lock allow-popups allow-popups-to-escape-sandbox allow-presentation allow-same-origin allow-scripts allow-top-navigation allow-top-navigation-by-user-activation"
        onLoad={handleIframeLoad}
        onError={handleIframeError}
      />

      {/* Video элемент для HLS/DASH потоков (если понадобится) */}
      {url.includes('.m3u8') || url.includes('.mpd') ? (
        <video
          ref={videoRef}
          className="w-full h-full"
          controls
          autoPlay
          onLoadedData={handleIframeLoad}
          onError={handleIframeError}
        >
          <source src={url} />
          Ваш браузер не поддерживает видео
        </video>
      ) : null}
    </div>
  );
}
