import { useEffect, useRef, useCallback } from 'react';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

class CacheManager {
  private cache = new Map<string, CacheEntry<any>>();

  set<T>(key: string, data: T, ttlMs: number = 5 * 60 * 1000): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttlMs,
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const isExpired = Date.now() - entry.timestamp > entry.ttl;
    if (isExpired) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }
}

// Глобальный кэш
const globalCache = new CacheManager();

/**
 * Хук для кэширования данных
 */
export function useCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttlMs: number = 5 * 60 * 1000
) {
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const fetchData = useCallback(async (): Promise<T | null> => {
    // Проверяем кэш
    const cached = globalCache.get<T>(key);
    if (cached) {
      return cached;
    }

    try {
      const data = await fetcher();
      if (isMountedRef.current) {
        globalCache.set(key, data, ttlMs);
      }
      return data;
    } catch (error) {
      console.error(`Cache fetch error for key ${key}:`, error);
      return null;
    }
  }, [key, fetcher, ttlMs]);

  return { fetchData, clearCache: () => globalCache.delete(key) };
}

/**
 * Хук для lazy loading элементов
 */
export function useLazyLoad(
  ref: React.RefObject<HTMLElement>,
  onVisible: () => void,
  options: IntersectionObserverInit = {}
) {
  useEffect(() => {
    if (!ref.current) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        onVisible();
        observer.unobserve(entry.target);
      }
    }, {
      threshold: 0.1,
      ...options,
    });

    observer.observe(ref.current);

    return () => {
      observer.disconnect();
    };
  }, [ref, onVisible, options]);
}

/**
 * Хук для дебаунса функции
 */
export function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (...args: Parameters<T>) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      callback(...args);
    }, delay);
  };
}

/**
 * Хук для мониторинга производительности
 */
export function usePerformanceMonitoring(componentName: string) {
  useEffect(() => {
    const startTime = performance.now();

    return () => {
      const endTime = performance.now();
      const renderTime = endTime - startTime;

      if (renderTime > 16.67) { // 60fps = 16.67ms per frame
        console.warn(
          `[Performance] ${componentName} took ${renderTime.toFixed(2)}ms to render`
        );
      }
    };
  }, [componentName]);
}

export { CacheManager, globalCache };
