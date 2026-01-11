import { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, X, AlertCircle, Loader } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Channel {
  title: string;
  url: string;
  type: 'web' | 'acestream';
}

export default function Player() {
  const [matchTitle, setMatchTitle] = useState('');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [currentChannelIndex, setCurrentChannelIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Инициализация Telegram Web App
  useEffect(() => {
    if (typeof window !== 'undefined' && 'Telegram' in window) {
      const tg = (window as any).Telegram.WebApp;
      tg.ready();
      tg.expand();
      tg.enableClosingConfirmation();
    }
  }, []);

  // Загрузка параметров из URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const link = params.get('link');
    const title = params.get('title');
    const channelsParam = params.get('channels');

    if (!link) {
      setError('Ссылка на трансляцию не найдена');
      setIsLoading(false);
      return;
    }

    setMatchTitle(title ? decodeURIComponent(title) : 'Трансляция');

    // Парсим каналы если есть
    if (channelsParam) {
      try {
        const parsedChannels = JSON.parse(decodeURIComponent(channelsParam));
        setChannels(parsedChannels);
      } catch (e) {
        console.error('Ошибка парсинга каналов:', e);
        setChannels([{ title: 'Основной', url: decodeURIComponent(link), type: 'web' }]);
      }
    } else {
      setChannels([{ title: 'Основной', url: decodeURIComponent(link), type: 'web' }]);
    }

    setIsLoading(false);
  }, []);

  const currentChannel = channels[currentChannelIndex];

  const handleSwitchChannel = (index: number) => {
    setCurrentChannelIndex(index);
    setError('');
  };

  const handleToggleFullscreen = async () => {
    if (!containerRef.current) return;

    try {
      if (!document.fullscreenElement) {
        await containerRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (err) {
      console.error('Ошибка полного экрана:', err);
    }
  };

  const handleCopyLink = () => {
    if (currentChannel) {
      navigator.clipboard.writeText(currentChannel.url).then(() => {
        if (typeof window !== 'undefined' && 'Telegram' in window) {
          const tg = (window as any).Telegram.WebApp;
          tg.showPopup({
            title: 'Скопировано',
            message: 'Ссылка скопирована в буфер обмена',
            buttons: [{ type: 'ok', text: 'OK' }]
          });
        }
      });
    }
  };

  const handleCloseApp = () => {
    if (typeof window !== 'undefined' && 'Telegram' in window) {
      const tg = (window as any).Telegram.WebApp;
      tg.close();
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Загрузка плеера...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md w-full">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-red-500 font-semibold mb-2">Ошибка</h3>
              <p className="text-white/80 text-sm">{error}</p>
              <Button onClick={handleCloseApp} variant="outline" className="mt-4 w-full">
                Закрыть
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentChannel?.type === 'acestream') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6 max-w-md w-full">
          <div className="text-center">
            <div className="text-4xl mb-4">🌀</div>
            <h3 className="text-blue-400 font-semibold mb-2 text-lg">Ace Stream трансляция</h3>
            <p className="text-white/80 text-sm mb-4">
              Для просмотра установите приложение Ace Stream Media
            </p>
            <div className="bg-slate-800/50 rounded p-3 mb-4">
              <code className="text-xs text-blue-300 break-all font-mono">
                {currentChannel.url.replace('acestream://', '')}
              </code>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCopyLink} className="flex-1" variant="default">
                📋 Копировать
              </Button>
              <Button onClick={handleCloseApp} variant="outline" className="flex-1">
                Закрыть
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`${isFullscreen ? 'fixed inset-0 z-50' : 'min-h-screen'} bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col`}
    >
      {/* Header */}
      {!isFullscreen && (
        <div className="bg-slate-900/80 backdrop-blur border-b border-slate-700/50 px-4 py-3 flex items-center justify-between">
          <div className="flex-1">
            <h1 className="text-white font-semibold text-sm truncate">📺 FutLive</h1>
            <p className="text-white/60 text-xs truncate">{matchTitle}</p>
          </div>
          <Button
            onClick={handleCloseApp}
            variant="ghost"
            size="sm"
            className="text-white/60 hover:text-white hover:bg-slate-700/50"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
      )}

      {/* Channel Tabs */}
      {channels.length > 1 && !isFullscreen && (
        <div className="bg-slate-800/50 border-b border-slate-700/50 px-4 py-2 overflow-x-auto">
          <div className="flex gap-2">
            {channels.map((channel, index) => (
              <button
                key={index}
                onClick={() => handleSwitchChannel(index)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                  index === currentChannelIndex
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700/50 text-white/70 hover:bg-slate-600/50'
                }`}
              >
                {channel.title}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Player Container */}
      <div className="flex-1 bg-black relative overflow-hidden">
        {currentChannel?.url.startsWith('http') ? (
          <iframe
            ref={iframeRef}
            src={currentChannel.url}
            className="w-full h-full border-none"
            allowFullScreen
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
            referrerPolicy="no-referrer"
            sandbox="allow-forms allow-modals allow-orientation-lock allow-pointer-lock allow-popups allow-popups-to-escape-sandbox allow-presentation allow-same-origin allow-scripts allow-top-navigation allow-top-navigation-by-user-activation"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <AlertCircle className="w-12 h-12 text-red-500" />
          </div>
        )}
      </div>

      {/* Controls */}
      {!isFullscreen && (
        <div className="bg-slate-900/80 backdrop-blur border-t border-slate-700/50 px-4 py-3 flex gap-2">
          <Button
            onClick={() => setIsMuted(!isMuted)}
            variant="outline"
            size="sm"
            className="text-white/70 hover:text-white hover:bg-slate-700/50"
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </Button>
          <Button
            onClick={handleCopyLink}
            variant="outline"
            size="sm"
            className="text-white/70 hover:text-white hover:bg-slate-700/50"
          >
            📋 Копировать
          </Button>
          <Button
            onClick={handleToggleFullscreen}
            variant="outline"
            size="sm"
            className="text-white/70 hover:text-white hover:bg-slate-700/50"
          >
            <Maximize className="w-4 h-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
