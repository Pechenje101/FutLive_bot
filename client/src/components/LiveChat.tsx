'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ChatMessage {
  id: string;
  author: string;
  text: string;
  timestamp: Date;
  isSystem?: boolean;
}

interface LiveChatProps {
  matchId: number;
  matchTitle: string;
  isOpen?: boolean;
}

export default function LiveChat({ matchId, matchTitle, isOpen = true }: LiveChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [userName] = useState(() => `User${Math.random().toString(36).substr(2, 9)}`);

  // Автоскролл к последнему сообщению
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Загрузка сообщений из localStorage
  useEffect(() => {
    const storedMessages = localStorage.getItem(`chat_${matchId}`);
    if (storedMessages) {
      try {
        const parsed = JSON.parse(storedMessages);
        setMessages(
          parsed.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          }))
        );
      } catch (e) {
        console.error('Failed to load chat messages:', e);
      }
    }

    // Добавляем системное сообщение о присоединении
    const joinMessage: ChatMessage = {
      id: `system_${Date.now()}`,
      author: 'Система',
      text: `${userName} присоединился к чату`,
      timestamp: new Date(),
      isSystem: true,
    };
    setMessages((prev) => [...prev, joinMessage]);
  }, [matchId, userName]);

  // Сохранение сообщений в localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`chat_${matchId}`, JSON.stringify(messages));
    }
  }, [messages, matchId]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    setIsLoading(true);
    try {
      const newMessage: ChatMessage = {
        id: `msg_${Date.now()}`,
        author: userName,
        text: inputValue.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, newMessage]);
      setInputValue('');

      // Имитация ответа других пользователей (в реальном приложении это будет WebSocket)
      if (Math.random() > 0.7) {
        setTimeout(() => {
          const reply: ChatMessage = {
            id: `msg_${Date.now()}_reply`,
            author: `User${Math.random().toString(36).substr(2, 5)}`,
            text: ['Согласен!', 'Отличный гол!', 'Ничего себе!', 'Вау!'][
              Math.floor(Math.random() * 4)
            ],
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, reply]);
        }, 1000 + Math.random() * 2000);
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Card className="flex flex-col h-full bg-background border-l">
      {/* Заголовок */}
      <div className="p-3 border-b">
        <h3 className="font-semibold text-sm truncate">💬 Live Chat</h3>
        <p className="text-xs text-muted-foreground truncate">{matchTitle}</p>
      </div>

      {/* Сообщения */}
      <ScrollArea className="flex-1 p-3">
        <div className="space-y-2">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground text-xs py-4">
              Чат пуст. Будьте первым!
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`text-xs ${msg.isSystem ? 'text-center text-muted-foreground italic' : ''}`}
              >
                {!msg.isSystem && (
                  <div className="flex gap-2">
                    <span className="font-medium text-primary truncate flex-shrink-0">
                      {msg.author}
                    </span>
                    <span className="text-muted-foreground text-xs flex-shrink-0">
                      {msg.timestamp.toLocaleTimeString('ru-RU', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}
                <p className={`${msg.isSystem ? '' : 'ml-0 mt-1'} break-words`}>
                  {msg.text}
                </p>
              </div>
            ))
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Ввод сообщения */}
      <div className="p-3 border-t space-y-2">
        <div className="flex gap-2">
          <Input
            placeholder="Ваше сообщение..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={isLoading}
            className="text-xs h-8"
            maxLength={200}
          />
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            size="sm"
            className="h-8 px-2 text-xs"
          >
            {isLoading ? '...' : 'Отправить'}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {inputValue.length}/200
        </p>
      </div>
    </Card>
  );
}
