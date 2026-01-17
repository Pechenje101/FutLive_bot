# 🎬 FutLive Player V2 - Production Deployment

Полностью готовый к production развертыванию проект для просмотра футбольных трансляций через Telegram Mini App.

## 🎯 Что включено

### Backend (Python + Flask)
- ✅ **API Server** - REST API для получения матчей и каналов
- ✅ **Telegram Bot** - интеграция с Telegram для управления матчами
- ✅ **Redis Cache** - кэширование матчей и данных пользователей
- ✅ **Sentry Monitoring** - отслеживание ошибок в production
- ✅ **Prometheus Metrics** - метрики производительности

### Frontend (React + TypeScript)
- ✅ **Web App** - встроенный плеер для просмотра трансляций
- ✅ **Video.js Player** - поддержка Ace Stream и других потоков
- ✅ **Sentry Integration** - мониторинг ошибок на frontend
- ✅ **Responsive Design** - адаптивный дизайн для мобильных устройств

### Infrastructure (Docker)
- ✅ **Docker Compose** - оркестрация всех сервисов
- ✅ **Nginx Proxy** - обратный прокси с SSL termination
- ✅ **Let's Encrypt SSL** - автоматические HTTPS сертификаты
- ✅ **Certbot Auto-Renewal** - автоматическое обновление сертификатов

---

## 🚀 Быстрый старт

### 1. Клонирование и подготовка

```bash
git clone https://github.com/your-username/futlive-player-v2.git
cd futlive-player-v2

# Запуск скрипта развертывания
./deploy.sh futlive.example.com admin@example.com your-telegram-token
```

### 2. Получение SSL сертификата

```bash
docker run -it --rm -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d futlive.example.com \
  --email admin@example.com \
  --agree-tos \
  --non-interactive
```

### 3. Запуск приложения

```bash
docker-compose build
docker-compose up -d
```

### 4. Проверка статуса

```bash
docker-compose ps
curl -k https://futlive.example.com/api/health
```

---

## 📊 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram User                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                    Telegram API
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Nginx (SSL/TLS)                            │
│              Port 80 (HTTP) & 443 (HTTPS)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌────────┐
    │ Backend │      │Frontend │      │ Redis  │
    │ (Flask) │      │(React) │      │(Cache) │
    └────────┘      └────────┘      └────────┘
        │
        └─────────► gooool365.org (Parser)
```

---

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_token

# API
API_URL=https://your-domain.com
FLASK_ENV=production

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# SSL
DOMAIN=your-domain.com
EMAIL=your-email@example.com

# Monitoring (Optional)
SENTRY_DSN=your-sentry-dsn
```

---

## 📈 Мониторинг

### Sentry (Error Tracking)
- Backend: Автоматически отслеживает ошибки Python
- Frontend: Отслеживает ошибки JavaScript

### Prometheus (Metrics)
- Доступно на `/metrics`
- Интегрируется с Grafana для визуализации

### Логи
- Сохраняются в `logs/` директории
- Доступны через `docker-compose logs`

---

## 🔐 Безопасность

- ✅ HTTPS/TLS шифрование
- ✅ Автоматическое обновление SSL сертификатов
- ✅ Firewall правила (рекомендуется)
- ✅ Sentry для отслеживания безопасности
- ✅ Rate limiting на API endpoints

---

## 🧹 Обслуживание

### Просмотр логов
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx
```

### Перезагрузка сервисов
```bash
docker-compose restart backend
docker-compose restart frontend
docker-compose restart redis
```

### Обновление приложения
```bash
git pull
docker-compose build
docker-compose up -d
```

### Очистка
```bash
docker-compose down -v
```

---

## 📞 Поддержка

Для решения проблем:

1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все переменные окружения установлены
3. Проверьте доступность `gooool365.org` с вашего сервера
4. Используйте Sentry для отслеживания ошибок

---

## 📚 Документация

- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Полное руководство развертывания
- [REDIS_NOTIFICATIONS_GUIDE.md](./REDIS_NOTIFICATIONS_GUIDE.md) - Система кэширования и уведомлений
- [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Интеграция компонентов

---

## 📝 Лицензия

MIT License
