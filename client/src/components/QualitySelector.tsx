'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface QualitySelectorProps {
  currentQuality: 'auto' | '720p' | '1080p';
  onQualityChange: (quality: 'auto' | '720p' | '1080p') => void;
  isLoading?: boolean;
}

const QUALITY_LABELS = {
  auto: 'Авто',
  '720p': '720p HD',
  '1080p': '1080p Full HD',
};

const QUALITY_ICONS = {
  auto: '⚙️',
  '720p': '📺',
  '1080p': '🎬',
};

export default function QualitySelector({
  currentQuality,
  onQualityChange,
  isLoading = false,
}: QualitySelectorProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={isLoading}
          className="gap-2 text-xs sm:text-sm"
        >
          <span>{QUALITY_ICONS[currentQuality]}</span>
          <span className="hidden sm:inline">{QUALITY_LABELS[currentQuality]}</span>
          <span className="sm:hidden">{currentQuality}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-32">
        {(Object.keys(QUALITY_LABELS) as Array<'auto' | '720p' | '1080p'>).map(
          (quality) => (
            <DropdownMenuItem
              key={quality}
              onClick={() => onQualityChange(quality)}
              className={currentQuality === quality ? 'bg-accent' : ''}
            >
              <span className="mr-2">{QUALITY_ICONS[quality]}</span>
              {QUALITY_LABELS[quality]}
              {currentQuality === quality && <span className="ml-auto">✓</span>}
            </DropdownMenuItem>
          )
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
