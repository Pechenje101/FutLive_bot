import { useEffect, useRef } from 'react';

interface GestureHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  onPinchZoom?: (scale: number) => void;
  onDoubleTap?: () => void;
}

interface TouchPoint {
  x: number;
  y: number;
  time: number;
}

const SWIPE_THRESHOLD = 50; // пиксели
const SWIPE_TIME_THRESHOLD = 300; // миллисекунды
const PINCH_THRESHOLD = 0.1; // 10% изменение

/**
 * Хук для обработки мобильных жестов (swipe, pinch-zoom, double-tap)
 */
export function useGestures(
  ref: React.RefObject<HTMLElement>,
  handlers: GestureHandlers
) {
  const touchStartRef = useRef<TouchPoint | null>(null);
  const touchEndRef = useRef<TouchPoint | null>(null);
  const lastTapRef = useRef<number>(0);
  const initialDistanceRef = useRef<number>(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // Обработка swipe жестов
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        touchStartRef.current = {
          x: touch.clientX,
          y: touch.clientY,
          time: Date.now(),
        };
      } else if (e.touches.length === 2) {
        // Инициализация pinch-zoom
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const distance = Math.hypot(
          touch2.clientX - touch1.clientX,
          touch2.clientY - touch1.clientY
        );
        initialDistanceRef.current = distance;
      }
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (e.changedTouches.length === 1) {
        const touch = e.changedTouches[0];
        touchEndRef.current = {
          x: touch.clientX,
          y: touch.clientY,
          time: Date.now(),
        };

        if (touchStartRef.current && touchEndRef.current) {
          handleSwipe();
        }

        // Double-tap обработка
        const now = Date.now();
        if (now - lastTapRef.current < 300) {
          handlers.onDoubleTap?.();
        }
        lastTapRef.current = now;
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && handlers.onPinchZoom) {
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const distance = Math.hypot(
          touch2.clientX - touch1.clientX,
          touch2.clientY - touch1.clientY
        );

        if (initialDistanceRef.current > 0) {
          const scale = distance / initialDistanceRef.current;
          if (Math.abs(scale - 1) > PINCH_THRESHOLD) {
            handlers.onPinchZoom(scale);
          }
        }
      }
    };

    const handleSwipe = () => {
      if (!touchStartRef.current || !touchEndRef.current) return;

      const deltaX = touchEndRef.current.x - touchStartRef.current.x;
      const deltaY = touchEndRef.current.y - touchStartRef.current.y;
      const deltaTime = touchEndRef.current.time - touchStartRef.current.time;

      // Проверяем, что это был быстрый свайп
      if (deltaTime > SWIPE_TIME_THRESHOLD) return;

      // Определяем направление свайпа
      const absDeltaX = Math.abs(deltaX);
      const absDeltaY = Math.abs(deltaY);

      if (absDeltaX > SWIPE_THRESHOLD && absDeltaX > absDeltaY) {
        // Горизонтальный свайп
        if (deltaX > 0) {
          handlers.onSwipeRight?.();
        } else {
          handlers.onSwipeLeft?.();
        }
      } else if (absDeltaY > SWIPE_THRESHOLD && absDeltaY > absDeltaX) {
        // Вертикальный свайп
        if (deltaY > 0) {
          handlers.onSwipeDown?.();
        } else {
          handlers.onSwipeUp?.();
        }
      }

      // Очищаем состояние
      touchStartRef.current = null;
      touchEndRef.current = null;
    };

    element.addEventListener('touchstart', handleTouchStart, false);
    element.addEventListener('touchend', handleTouchEnd, false);
    element.addEventListener('touchmove', handleTouchMove, false);

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
      element.removeEventListener('touchmove', handleTouchMove);
    };
  }, [handlers]);
}

/**
 * Хук для обработки клавиатурных сокращений
 */
export function useKeyboardShortcuts(
  shortcuts: Record<string, () => void>
) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      
      // Пропускаем если фокус на input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Проверяем комбинации клавиш
      const shortcutKey = [
        e.ctrlKey && 'ctrl',
        e.shiftKey && 'shift',
        e.altKey && 'alt',
        key,
      ]
        .filter(Boolean)
        .join('+');

      if (shortcuts[shortcutKey]) {
        e.preventDefault();
        shortcuts[shortcutKey]();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}
