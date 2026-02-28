# 🚀 Деплой FutLive на Vercel

## ✅ Что уже готово

### API Routes
- `/api/stream-proxy` - Прокси для обхода X-Frame-Options
- `/api/player-proxy` - Базовый прокси плеера
- `/api/livetv-player` - Извлечение embed URLs и Ace Stream ссылок
- `/api/matches` - Получение списка матчей
- `/api/event` - Обработка событий

### Web App (`/`)
- HLS плеер для Ace Stream
- Прокси-режим для LiveTV iframe
- Переключатель режимов (прокси/напрямую)
- Мобильный Telegram Web App UI

---

## 📦 Деплой на Vercel

### Вариант 1: Через GitHub (рекомендуется)

1. **Push кода в репозиторий**
   ```bash
   git add .
   git commit -m "Add stream proxy for Vercel"
   git push
   ```

2. **Импорт в Vercel**
   - Откройте https://vercel.com/new
   - Выберите репозиторий FutLive
   - Framework Preset: Next.js
   - Нажмите "Deploy"

3. **Получите URL**
   - После деплоя получите URL вида: `https://futlive-xxx.vercel.app`

### Вариант 2: Через Vercel CLI

1. **Установка CLI**
   ```bash
   npm i -g vercel
   ```

2. **Деплой**
   ```bash
   vercel --prod
   ```

---

## ⚙️ Конфигурация

### vercel.json
```json
{
  "functions": {
    "src/app/api/stream-proxy/route.ts": {
      "memory": 1024,
      "maxDuration": 30
    }
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" }
      ]
    }
  ]
}
```

### Переменные окружения (опционально)
```
TELEGRAM_BOT_TOKEN=your_bot_token
GITHUB_TOKEN=ghp_xxx
```

---

## 🔗 Интеграция с Telegram Bot

### Обновление Web App URL в боте

В `bot_final.py` замените:
```python
WEB_APP_URL = "https://your-vercel-app.vercel.app"
```

### Полный URL для Web App
```
https://your-app.vercel.app/?title=Team%20A%20vs%20Team%20B&time=20:00&status=LIVE&url=https://livetv.sx/event/123&acestreams=["acestream://xxx"]
```

---

## 🎯 Как работает прокси

### Проблема
LiveTV блокирует iframe через заголовок:
```
X-Frame-Options: SAMEORIGIN
```

### Решение
1. Запрос идёт на `/api/stream-proxy?url=...`
2. Сервер Vercel делает запрос к LiveTV
3. Удаляет блокирующие заголовки
4. Перезаписывает URL в контенте на прокси
5. Возвращает контент без X-Frame-Options

### Схема
```
User Browser
    ↓
Vercel API (/api/stream-proxy)
    ↓
LiveTV Server
    ↓ (без X-Frame-Options)
User iframe
```

---

## 📱 Использование

### Переключатель режимов
- **🌐 Прокси** - Использовать серверный прокси (обходит блокировку)
- **🔗 Напрямую** - Прямое подключение к LiveTV (может не работать в iframe)

### Ace Stream
Требует установленный Ace Stream Engine на устройстве пользователя:
- Windows/Mac: https://acestream.org
- Android: Google Play "Ace Stream Media"
- iOS: Ограниченная поддержка

---

## ⚠️ Ограничения

### Vercel Free Tier
- 100 GB bandwidth/месяц
- 100 GB serverless function execution/месяц
- 10 секунд timeout для API routes
- Cold starts для serverless functions

### Рекомендации
1. Используйте Ace Stream где возможно (меньше нагрузки на прокси)
2. Кэшируйте ответы на клиенте
3. Для высокого трафика - перейдите на Pro план

---

## 🔄 Альтернативы Vercel

| Платформа | Бесплатно | Serverless | API Routes |
|-----------|-----------|------------|------------|
| Vercel | ✅ | ✅ | ✅ |
| Netlify | ✅ | ✅ | Functions |
| Railway | $5 кредит | ✅ | ✅ |
| Render | ✅ | ✅ | ✅ |
| Fly.io | ✅ | ✅ | ✅ |

---

## 🛠️ Разработка локально

```bash
# Установка зависимостей
bun install

# Запуск dev сервера
bun run dev

# Проверка линтера
bun run lint
```

Сервер запустится на http://localhost:3000

---

## 📊 Структура проекта

```
src/
├── app/
│   ├── page.tsx           # Главная страница Web App
│   ├── layout.tsx         # Layout
│   ├── globals.css        # Стили
│   └── api/
│       ├── stream-proxy/  # Основной прокси
│       ├── player-proxy/  # Прокси плеера
│       ├── livetv-player/ # Извлечение ссылок
│       ├── matches/       # Список матчей
│       └── event/         # Обработка событий
├── components/            # React компоненты
└── lib/                   # Утилиты

vercel.json               # Конфигурация Vercel
package.json              # Зависимости
```

---

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте логи Vercel Dashboard
2. Убедитесь, что URL правильно закодирован
3. Попробуйте переключить режим прокси
4. Используйте прямые ссылки на LiveTV как fallback
