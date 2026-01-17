# 🚀 Инструкция по развертыванию FutLive Player V2

Полное руководство по развертыванию приложения на production сервере с Docker, SSL и мониторингом.

---

## 📋 Требования

- **VPS/Сервер** с доступом к `gooool365.org` (рекомендуется Европа/США)
- **Docker** и **Docker Compose** установлены
- **Домен** (для SSL сертификата)
- **Telegram Bot Token** (получить от @BotFather)
- **Sentry DSN** (опционально, для мониторинга ошибок)

---

## 🔧 Шаг 1: Подготовка сервера

### 1.1 Установка Docker и Docker Compose

```bash
# Обновление системы
sudo apt-get update && sudo apt-get upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt-get install -y docker-compose

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### 1.2 Клонирование проекта

```bash
# Клонирование репозитория
git clone https://github.com/your-username/futlive-player-v2.git
cd futlive-player-v2

# Создание необходимых директорий
mkdir -p certbot/conf certbot/www logs
```

---

## 🔐 Шаг 2: Конфигурация переменных окружения

### 2.1 Создание .env файла

```bash
cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# API Configuration
API_URL=https://your-domain.com
FLASK_ENV=production

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Sentry Configuration (Optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# SSL Configuration
DOMAIN=your-domain.com
EMAIL=your-email@example.com

# Application Version
APP_VERSION=1.0.0
EOF
```

### 2.2 Замена значений

Отредактируйте `.env` файл и замените:
- `your_telegram_bot_token` → ваш реальный токен от @BotFather
- `your-domain.com` → ваш домен (например, `futlive.example.com`)
- `your-email@example.com` → ваш email для SSL уведомлений
- `your-sentry-dsn` → ваш Sentry DSN (если используете мониторинг)

---

## 🔒 Шаг 3: Получение SSL сертификата

### 3.1 Инициализация Let's Encrypt

```bash
# Создание директорий для certbot
mkdir -p certbot/conf certbot/www

# Запуск certbot для получения сертификата
docker run -it --rm -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d your-domain.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

### 3.2 Проверка сертификата

```bash
ls -la certbot/conf/live/your-domain.com/
# Должны быть файлы: fullchain.pem, privkey.pem
```

---

## 🐳 Шаг 4: Запуск Docker контейнеров

### 4.1 Сборка образов

```bash
# Сборка всех контейнеров
docker-compose build
```

### 4.2 Запуск приложения

```bash
# Запуск в фоне
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### 4.3 Проверка здоровья приложения

```bash
# Проверка API
curl -k https://your-domain.com/api/health

# Должен вернуть:
# {"status":"OK","success":true,"version":"1.0.0"}
```

---

## 📊 Шаг 5: Настройка мониторинга

### 5.1 Sentry (Отслеживание ошибок)

1. Создайте аккаунт на [sentry.io](https://sentry.io)
2. Создайте новый проект для Python (Backend)
3. Скопируйте DSN и добавьте в `.env`:
   ```bash
   SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
   ```
4. Перезагрузите контейнер:
   ```bash
   docker-compose restart backend
   ```

### 5.2 Prometheus (Метрики производительности)

Метрики доступны по адресу:
```
https://your-domain.com/metrics
```

Используйте Prometheus для сбора метрик:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'futlive'
    static_configs:
      - targets: ['https://your-domain.com/metrics']
```

---

## 🔄 Шаг 6: Автоматическое обновление SSL

SSL сертификат автоматически обновляется контейнером `certbot` каждые 12 часов.

Для ручного обновления:
```bash
docker-compose exec certbot certbot renew --force-renewal
docker-compose restart nginx
```

---

## 📱 Шаг 7: Настройка Telegram Mini App

1. Откройте @BotFather в Telegram
2. Выберите ваш бот и команду `/setmenubutton`
3. Установите URL Web App:
   ```
   https://your-domain.com
   ```
4. Сохраните изменения

---

## 🧹 Шаг 8: Обслуживание

### Просмотр логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx
```

### Перезагрузка сервисов

```bash
# Перезагрузить все
docker-compose restart

# Перезагрузить конкретный сервис
docker-compose restart backend
```

### Остановка приложения

```bash
docker-compose down
```

### Очистка данных

```bash
# Удалить все контейнеры и тома
docker-compose down -v
```

---

## 🐛 Решение проблем

### Проблема: "Connection refused" при подключении к API

**Решение:**
```bash
# Проверьте логи backend
docker-compose logs backend

# Перезагрузите backend контейнер
docker-compose restart backend
```

### Проблема: SSL сертификат не обновляется

**Решение:**
```bash
# Проверьте логи certbot
docker-compose logs certbot

# Ручное обновление
docker-compose exec certbot certbot renew --force-renewal
```

### Проблема: Redis не подключается

**Решение:**
```bash
# Проверьте Redis
docker-compose exec redis redis-cli ping
# Должен вернуть: PONG

# Перезагрузите Redis
docker-compose restart redis
```

---

## 📈 Мониторинг производительности

### Метрики API

Доступные метрики на `/metrics`:
- `futlive_app_info` - информация о приложении
- `flask_http_request_duration_seconds` - время обработки запросов
- `flask_http_request_total` - количество запросов

### Логирование

Все логи сохраняются в директорию `logs/`:
- `api-server.log` - логи API сервера
- `telegram-bot.log` - логи Telegram бота

---

## 🔐 Безопасность

### Рекомендации

1. **Используйте firewall:**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Регулярно обновляйте:**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

3. **Мониторьте логи:**
   ```bash
   docker-compose logs -f | grep ERROR
   ```

4. **Используйте Sentry для отслеживания ошибок**

---

## 📞 Поддержка

Если у вас возникли проблемы:

1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все переменные окружения установлены
3. Проверьте доступность `gooool365.org` с вашего сервера
4. Используйте Sentry для отслеживания ошибок

---

## 📝 Лицензия

MIT License - см. LICENSE файл для деталей
