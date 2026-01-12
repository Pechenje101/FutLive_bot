'use client';

import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import VideoJsPlayer from '@/components/VideoJsPlayer';
import { getMatch, getChannels, type Match, type Channel } from '@/lib/api';

export default function Player() {
  const [match, setMatch] = useState<Match | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [currentChannelIndex, setCurrentChannelIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Инициализация Telegram Web App
  useEffect(() => {
    if (typeof window !== 'undefined' && 'Telegram' in window) {
      const tg = (window as any).Telegram.WebApp;
      tg.ready();
      tg.expand();
      tg.enableClosingConfirmation();
    }
  }, []);

  // Загрузка данных матча
  useEffect(() => {
    const loadMatch = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Получаем matchId из URL параметров
        const params = new URLSearchParams(window.location.search);
        const matchIdParam = params.get('match_id');
        const matchId = matchIdParam ? parseInt(matchIdParam, 10) : 0;

        // Загружаем матч
        const matchResponse = await getMatch(matchId);
        if (!matchResponse.success || !matchResponse.data) {
          setError(matchResponse.error || 'Не удалось загрузить матч');
          setIsLoading(false);
          return;
        }

        setMatch(matchResponse.data);

        // Загружаем каналы
        const channelsResponse = await getChannels(matchId);
        if (!channelsResponse.success || !channelsResponse.data) {
          setError(channelsResponse.error || 'Не удалось загрузить каналы');
          setIsLoading(false);
          return;
        }

        setChannels(channelsResponse.data);
        setCurrentChannelIndex(0);
        setIsLoading(false);
      } catch (err) {
        setError(`Ошибка при загрузке данных: ${err}`);
        setIsLoading(false);
      }
    };

    loadMatch();
  }, []);

  const currentChannel = channels[currentChannelIndex];

  const handlePreviousChannel = () => {
    setCurrentChannelIndex((prev) => (prev > 0 ? prev - 1 : channels.length - 1));
  };

  const handleNextChannel = () => {
    setCurrentChannelIndex((prev) => (prev < channels.length - 1 ? prev + 1 : 0));
  };

  const handlePlayerError = (errorMsg: string) => {
    console.error('Player error:', errorMsg);
    // Автоматически переходим на следующий канал при ошибке
    if (channels.length > 1) {
      setTimeout(() => {
        handleNextChannel();
      }, 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="w-full h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          <p className="text-white text-lg font-medium">Загрузка трансляции...</p>
        </div>
      </div>
    );
  }

  if (error || !match || channels.length === 0) {
    return (
      <div className="w-full h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="text-red-500 text-6xl">⚠️</div>
          <p className="text-white text-lg font-medium">Ошибка загрузки</p>
          <p className="text-gray-400 text-sm">{error || 'Матч или каналы не найдены'}</p>
          <Button
            onClick={() => window.history.back()}
            className="mt-4 bg-blue-600 hover:bg-blue-700"
          >
            Вернуться назад
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col">
      {/* Заголовок */}
      <div className="bg-black/40 backdrop-blur-sm border-b border-white/10 px-4 py-3">
        <h1 className="text-white font-bold text-lg truncate">{match.title}</h1>
        <p className="text-gray-400 text-xs mt-1">
          Канал {currentChannelIndex + 1} из {channels.length}
        </p>
      </div>

      {/* Плеер */}
      <div className="flex-1 flex items-center justify-center bg-black p-2 sm:p-4">
        <div className="w-full h-full max-w-6xl">
          {currentChannel && (
            <VideoJsPlayer
              url={currentChannel.url}
              title={currentChannel.title}
              onError={handlePlayerError}
            />
          )}
        </div>
      </div>

      {/* Информация о канале и управление */}
      <div className="bg-black/40 backdrop-blur-sm border-t border-white/10 p-4 space-y-3">
        {/* Название текущего канала */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-white font-semibold text-sm">{currentChannel?.title}</p>
            <p className="text-gray-400 text-xs mt-1">
              {currentChannel?.url.startsWith('acestream://')
                ? '🎬 Ace Stream'
                : currentChannel?.url.includes('m3u8')
                ? '📺 HLS Поток'
                : '🌐 Веб-плеер'}
            </p>
          </div>
        </div>

        {/* Управление каналами */}
        {channels.length > 1 && (
          <div className="flex gap-2 items-center justify-between">
            <Button
              onClick={handlePreviousChannel}
              variant="outline"
              size="sm"
              className="flex-1 bg-white/10 hover:bg-white/20 border-white/20 text-white"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Предыдущий
            </Button>

            {/* Список каналов (горизонтальный скролл) */}
            <div className="flex gap-2 overflow-x-auto flex-1 pb-2">
              {channels.map((channel, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentChannelIndex(index)}
                  className={`px-3 py-1 rounded text-xs font-medium whitespace-nowrap transition-all ${
                    index === currentChannelIndex
                      ? 'bg-blue-600 text-white'
                      : 'bg-white/10 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  {index + 1}
                </button>
              ))}
            </div>

            <Button
              onClick={handleNextChannel}
              variant="outline"
              size="sm"
              className="flex-1 bg-white/10 hover:bg-white/20 border-white/20 text-white"
            >
              Следующий
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        )}

        {/* Информация о потоке */}
        <div className="bg-white/5 rounded p-2 text-xs text-gray-400 border border-white/10">
          <p className="truncate">
            <span className="text-gray-500">URL:</span> {currentChannel?.url.substring(0, 50)}...
          </p>
        </div>
      </div>
    </div>
  );
}
