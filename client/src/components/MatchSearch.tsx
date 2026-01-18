'use client';

import { useState, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDebounce } from '@/hooks/usePerformanceOptimization';

interface MatchSearchProps {
  onSearch: (query: string) => void;
  onFilterChange: (filter: string) => void;
  isLoading?: boolean;
}

const FILTER_OPTIONS = [
  { value: 'all', label: '📺 Все матчи' },
  { value: 'football', label: '⚽ Футбол' },
  { value: 'hockey', label: '🏒 Хоккей' },
  { value: 'basketball', label: '🏀 Баскетбол' },
  { value: 'tennis', label: '🎾 Теннис' },
  { value: 'biathlon', label: '🎿 Биатлон' },
];

export default function MatchSearch({
  onSearch,
  onFilterChange,
  isLoading = false,
}: MatchSearchProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all');

  const debouncedSearch = useDebounce((query: string) => {
    onSearch(query);
  }, 300);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const query = e.target.value;
      setSearchQuery(query);
      debouncedSearch(query);
    },
    [debouncedSearch]
  );

  const handleFilterChange = useCallback(
    (value: string) => {
      setSelectedFilter(value);
      onFilterChange(value);
    },
    [onFilterChange]
  );

  const handleClear = useCallback(() => {
    setSearchQuery('');
    setSelectedFilter('all');
    onSearch('');
    onFilterChange('all');
  }, [onSearch, onFilterChange]);

  return (
    <div className="space-y-3">
      {/* Поиск */}
      <div className="flex gap-2">
        <Input
          placeholder="Поиск матча..."
          value={searchQuery}
          onChange={handleSearchChange}
          disabled={isLoading}
          className="flex-1"
        />
        {(searchQuery || selectedFilter !== 'all') && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClear}
            disabled={isLoading}
          >
            ✕
          </Button>
        )}
      </div>

      {/* Фильтр */}
      <Select value={selectedFilter} onValueChange={handleFilterChange} disabled={isLoading}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {FILTER_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Подсказка */}
      {searchQuery && (
        <p className="text-xs text-muted-foreground">
          Поиск по: "{searchQuery}"
        </p>
      )}
    </div>
  );
}
