# FutLive Player V2 - GitHub Deployment

[![Deploy to VPS](https://github.com/yourusername/futlive-player-v2/actions/workflows/deploy.yml/badge.svg)](https://github.com/yourusername/futlive-player-v2/actions/workflows/deploy.yml)

Полнофункциональное приложение для просмотра футбольных трансляций через Telegram Mini App с автоматическим развертыванием на VPS через GitHub Actions.

## 🎯 Функции

- 🤖 **Telegram Bot** - Интерфейс для выбора матчей
- 📱 **Web App** - Встроенный плеер с поддержкой Ace Stream
- 🎬 **Video.js Player** - Профессиональный плеер с качеством видео
- 💬 **Live Chat** - Обсуждение матча в реальном времени
- 📊 **Match Stats** - Статистика матча (голы, карточки)
- 🔔 **Notifications** - Напоминания за 15 минут до матча
- 💾 **Redis Cache** - Кэширование для масштабируемости
- 🌙 **Dark/Light Mode** - Поддержка темного режима
- 📈 **Monitoring** - Sentry + Prometheus

## 🚀 Быстрый старт

### Локальное развертывание

```bash
# Установка зависимостей
pnpm install

# Запуск всех компонентов
./start_all.sh

# Откройте http://localhost:3000
```

### Развертывание на VPS через GitHub Actions

1. **Подготовьте VPS:**
   ```bash
   ssh root@YOUR_VPS_IP
   curl -fsSL https://raw.githubusercontent.com/yourusername/futlive-player-v2/main/scripts/setup-vps.sh | sudo bash
   ```

2. **Добавьте GitHub Secrets:**
   - `VPS_HOST` - IP адрес VPS
   - `VPS_USER` - SSH пользователь
   - `VPS_PORT` - SSH порт
   - `VPS_SSH_KEY` - Приватный SSH ключ

3. **Загрузите на GitHub:**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

4. **GitHub Actions автоматически развернет!**

## 📚 Документация

- [QUICK_START_GITHUB.md](./QUICK_START_GITHUB.md) - Быстрый старт (5 минут)
- [GITHUB_DEPLOYMENT.md](./GITHUB_DEPLOYMENT.md) - Полное руководство
- [GITHUB_SECRETS.md](./GITHUB_SECRETS.md) - Настройка Secrets
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Руководство по развертыванию
- [PRODUCTION_README.md](./PRODUCTION_README.md) - Production конфигурация
- [QA_REPORT.md](./QA_REPORT.md) - Отчет о качестве (оценка 9.1/10)

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────┐
│                   Telegram Bot                      │
│              (Python + python-telegram-bot)         │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│                  Web App (Frontend)                 │
│         (React 19 + Tailwind + Video.js)            │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│                  API Server                         │
│            (Flask + Python + Async)                 │
├─────────────────────────────────────────────────────┤
│  ├─ /api/matches - Список матчей                   │
│  ├─ /api/match/{id} - Конкретный матч              │
│  ├─ /api/channels/{id} - Каналы матча              │
│  └─ /api/health - Статус сервера                   │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
    ┌────────┐  ┌────────┐  ┌──────────┐
    │ Redis  │  │ Parser │  │ Sentry   │
    │ Cache  │  │ (gooool)  │ Monitor  │
    └────────┘  └────────┘  └──────────┘
```

## 🔄 CI/CD Pipeline

```yaml
GitHub Push
    ↓
GitHub Actions
    ├─ Test (TypeScript, Lint)
    ├─ Build (Frontend)
    └─ Deploy (SSH to VPS)
        ├─ git pull
        ├─ pnpm install
        ├─ docker-compose up
        └─ ✅ Done!
```

## 📦 Стек технологий

**Frontend:**
- React 19
- TypeScript
- Tailwind CSS 4
- Video.js
- Wouter (routing)

**Backend:**
- Python 3.11
- Flask
- Redis
- Docker

**DevOps:**
- GitHub Actions
- Docker & Docker Compose
- Nginx
- Let's Encrypt SSL

**Monitoring:**
- Sentry
- Prometheus
- Grafana (опционально)

## 🔐 Безопасность

- ✅ SSL/TLS (Let's Encrypt)
- ✅ SSH ключи для CI/CD
- ✅ Environment variables для конфиденциальных данных
- ✅ Firewall на VPS
- ✅ Rate limiting на API
- ✅ CORS protection

## 📊 Производительность

- ⚡ Кэширование Redis (5 мин - 30 дней)
- ⚡ Lazy loading компонентов
- ⚡ Code splitting
- ⚡ Gzip compression
- ⚡ CDN для статических файлов

**Оценка Lighthouse:** 85+

## 🐛 Решение проблем

### GitHub Actions не может подключиться к VPS

```bash
# Проверьте SSH ключ
ssh -i ~/.ssh/github_deploy ubuntu@YOUR_VPS_IP

# Проверьте Secrets в GitHub Settings
```

### Docker контейнеры не запускаются

```bash
# На VPS
docker-compose logs -f
docker-compose restart
```

### SSL сертификат истек

```bash
# На VPS
sudo certbot renew --force-renewal
sudo systemctl restart nginx
```

Смотрите полную документацию в [GITHUB_DEPLOYMENT.md](./GITHUB_DEPLOYMENT.md)

## 🎯 Следующие шаги

1. **Оптимизировать размер бандла** - удалить неиспользуемые библиотеки
2. **Добавить unit тесты** - vitest для критических функций
3. **Реализовать WebSocket** - для real-time chat
4. **Добавить платежи** - Stripe для премиум-функций

## 📞 Поддержка

- 📖 Смотрите документацию в папке `/docs`
- 🐛 Создавайте Issues для проблем
- 💬 Обсуждайте в Discussions

## 📄 Лицензия

MIT License - смотрите [LICENSE](./LICENSE)

## 🙏 Благодарности

- [Video.js](https://videojs.com/) - видео плеер
- [Tailwind CSS](https://tailwindcss.com/) - стили
- [Flask](https://flask.palletsprojects.com/) - backend
- [Docker](https://www.docker.com/) - контейнеризация

---

**Сделано с ❤️ для футбольных фанатов**

```
🚀 Развертывание: GitHub Actions + VPS
📱 Интерфейс: Telegram Mini App
🎬 Плеер: Video.js + Ace Stream
🔔 Уведомления: Redis + Telegram
```
