# FutLive Bot 🤖⚽

Telegram бот для поиска и просмотра спортивных трансляций в реальном времени.

## Функционал

- 📺 Поиск текущих и предстоящих спортивных событий на livetv.sx
- ⚽ Фильтрация по видам спорта (Футбол, Теннис, Хоккей, Баскетбол и т.д.)
- 🔴 Показ статуса матча (LIVE или UPCOMING)
- ⏱️ Отображение времени начала события
- 🔗 Прямые ссылки на трансляции

## Технологический стек

- **Python 3.11+**
- **aiogram 3.3.0** - Telegram Bot API
- **Playwright** - Парсинг динамического контента
- **BeautifulSoup4** - Парсинг HTML

## Установка

```bash
pip install -r requirements.txt
playwright install chromium
```

## Запуск

```bash
python bot_final.py
```

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота (от @BotFather)

## Структура проекта

```
.
├── bot_final.py          # Основной бот
├── match_finder.py       # Парсер матчей с livetv.sx
├── parser.py             # Парсер матчей (резервный)
├── requirements.txt      # Зависимости
├── Dockerfile            # Docker образ для деплоя
├── render.yaml           # Конфигурация для Render.com
└── .github/workflows/
    └── telegram-bot.yml  # GitHub Actions workflow
```

---

## 🚀 Деплой для 24/7 работы

### ⚠️ Важно: GitHub Actions НЕ подходит для 24/7 работы!

GitHub Actions имеет ограничения:
- **Бесплатный план**: максимум 6 часов на один workflow
- **Платный план**: максимум 35 часов на один workflow
- Бот будет периодически отключаться

### Рекомендуемые варианты для 24/7 работы:

---

### Вариант 1: Render.com (БЕСПЛАТНО) ⭐ Рекомендуется

1. **Создай аккаунт на [render.com](https://render.com)**

2. **Подключи GitHub репозиторий**

3. **Создай новый Background Worker:**
   - New → Background Worker
   - Подключи репозиторий `Pechenje101/FutLive_bot`
   - Render автоматически определит `render.yaml`

4. **Или создай вручную:**
   - Environment: Docker
   - Branch: main
   - Plan: Free

5. **Добавь переменную окружения:**
   - `TELEGRAM_BOT_TOKEN` = твой_токен_от_BotFather

6. **Деплой!** Render автоматически запустит бота

**Преимущества Render:**
- ✅ Бесплатный план (750 часов/месяц)
- ✅ Автоматический перезапуск при падении
- ✅ Логи в реальном времени
- ✅ Автодеплой при push в репозиторий

---

### Вариант 2: Railway.app (Платно после триала)

1. Создай аккаунт на [railway.app](https://railway.app)
2. Подключи GitHub репозиторий
3. Добавь переменную `TELEGRAM_BOT_TOKEN`
4. Railway автоматически определит Dockerfile

---

### Вариант 3: VPS сервер (Самый надежный)

Если у тебя есть VPS (например, на Timeweb, Reg.ru, Hetzner):

```bash
# Подключись к серверу по SSH
ssh user@your-server

# Клонируй репозиторий
git clone https://github.com/Pechenje101/FutLive_bot.git
cd FutLive_bot

# Установи зависимости
pip install -r requirements.txt
playwright install chromium

# Создай .env файл
echo "TELEGRAM_BOT_TOKEN=твой_токен" > .env

# Запусти через systemd для автозапуска
```

**Создай systemd сервис** `/etc/systemd/system/futlive-bot.service`:

```ini
[Unit]
Description=FutLive Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/FutLive_bot
Environment=TELEGRAM_BOT_TOKEN=твой_токен
ExecStart=/usr/bin/python3 bot_final.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable futlive-bot
sudo systemctl start futlive-bot
```

---

## GitHub Actions (Резервный вариант)

Workflow настроен на запуск каждый час. Это НЕ обеспечивает 24/7 работу, но может использоваться как резерв.

Для настройки:
1. Settings → Secrets and variables → Actions
2. Добавь `TELEGRAM_BOT_TOKEN`

---

## Автор

FutLive Bot Team
