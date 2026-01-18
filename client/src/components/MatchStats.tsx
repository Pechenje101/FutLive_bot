'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Goal {
  player: string;
  minute: number;
  isOwnGoal?: boolean;
}

interface Card {
  player: string;
  minute: number;
  color: 'yellow' | 'red';
}

interface TeamStats {
  name: string;
  score: number;
  goals: Goal[];
  cards: Card[];
  possession?: number;
  shots?: number;
  shotsOnTarget?: number;
}

interface MatchStatsProps {
  homeTeam: TeamStats;
  awayTeam: TeamStats;
  status: 'live' | 'finished' | 'upcoming';
  minute?: number;
}

export default function MatchStats({
  homeTeam,
  awayTeam,
  status,
  minute,
}: MatchStatsProps) {
  const getStatusLabel = () => {
    switch (status) {
      case 'live':
        return `🔴 LIVE ${minute ? `${minute}'` : ''}`;
      case 'finished':
        return '✅ Завершено';
      case 'upcoming':
        return '⏰ Предстоит';
      default:
        return '';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'live':
        return 'bg-red-500/20 text-red-700 dark:text-red-400';
      case 'finished':
        return 'bg-green-500/20 text-green-700 dark:text-green-400';
      case 'upcoming':
        return 'bg-blue-500/20 text-blue-700 dark:text-blue-400';
      default:
        return '';
    }
  };

  return (
    <div className="space-y-3">
      {/* Статус и счет */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <Badge className={getStatusColor()}>{getStatusLabel()}</Badge>
        </div>

        <div className="grid grid-cols-3 gap-4 items-center">
          {/* Домашняя команда */}
          <div className="text-center">
            <p className="font-semibold text-sm truncate">{homeTeam.name}</p>
            <p className="text-2xl font-bold text-primary">{homeTeam.score}</p>
          </div>

          {/* Разделитель */}
          <div className="flex justify-center">
            <div className="text-center">
              <p className="text-xs text-muted-foreground">VS</p>
            </div>
          </div>

          {/* Гостевая команда */}
          <div className="text-center">
            <p className="font-semibold text-sm truncate">{awayTeam.name}</p>
            <p className="text-2xl font-bold text-primary">{awayTeam.score}</p>
          </div>
        </div>
      </Card>

      {/* Голеадоры */}
      {(homeTeam.goals.length > 0 || awayTeam.goals.length > 0) && (
        <Card className="p-3">
          <h4 className="font-semibold text-xs mb-2">⚽ Голы</h4>
          <div className="space-y-2">
            {homeTeam.goals.map((goal, idx) => (
              <div key={idx} className="flex justify-between text-xs">
                <span className="text-muted-foreground">{goal.minute}'</span>
                <span className="font-medium">{goal.player}</span>
                <span className="text-primary">{homeTeam.name}</span>
              </div>
            ))}
            {awayTeam.goals.map((goal, idx) => (
              <div key={idx} className="flex justify-between text-xs">
                <span className="text-muted-foreground">{goal.minute}'</span>
                <span className="font-medium">{goal.player}</span>
                <span className="text-primary">{awayTeam.name}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Карточки */}
      {(homeTeam.cards.length > 0 || awayTeam.cards.length > 0) && (
        <Card className="p-3">
          <h4 className="font-semibold text-xs mb-2">🟨 Карточки</h4>
          <div className="space-y-2">
            {homeTeam.cards.map((card, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">{card.minute}'</span>
                <span className="font-medium flex-1">{card.player}</span>
                <div
                  className={`w-3 h-4 rounded ${
                    card.color === 'yellow' ? 'bg-yellow-400' : 'bg-red-500'
                  }`}
                />
              </div>
            ))}
            {awayTeam.cards.map((card, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">{card.minute}'</span>
                <span className="font-medium flex-1">{card.player}</span>
                <div
                  className={`w-3 h-4 rounded ${
                    card.color === 'yellow' ? 'bg-yellow-400' : 'bg-red-500'
                  }`}
                />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Статистика */}
      {(homeTeam.possession || homeTeam.shots) && (
        <Card className="p-3">
          <h4 className="font-semibold text-xs mb-3">📊 Статистика</h4>
          <div className="space-y-2">
            {homeTeam.possession && (
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>{homeTeam.possession}%</span>
                  <span>Владение мячом</span>
                  <span>{awayTeam.possession}%</span>
                </div>
                <div className="flex h-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="bg-primary"
                    style={{ width: `${homeTeam.possession}%` }}
                  />
                  <div
                    className="bg-secondary"
                    style={{ width: `${awayTeam.possession}%` }}
                  />
                </div>
              </div>
            )}
            {homeTeam.shots && (
              <div className="flex justify-between text-xs">
                <span>{homeTeam.shots}</span>
                <span>Удары</span>
                <span>{awayTeam.shots}</span>
              </div>
            )}
            {homeTeam.shotsOnTarget && (
              <div className="flex justify-between text-xs">
                <span>{homeTeam.shotsOnTarget}</span>
                <span>Удары в створ</span>
                <span>{awayTeam.shotsOnTarget}</span>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
