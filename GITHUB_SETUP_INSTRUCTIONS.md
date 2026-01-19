# 🚀 GitHub Actions Setup - Инструкции по настройке

Проект успешно загружен на GitHub! Теперь нужно настроить GitHub Secrets для автоматического развертывания.

## 📋 Шаг 1: Добавьте GitHub Secrets

Откройте: https://github.com/Pechenje101/FutLive_bot/settings/secrets/actions

Нажмите "New repository secret" и добавьте следующие переменные:

### 🔐 Обязательные Secrets (для CI/CD):

| Имя | Значение | Описание |
|-----|----------|---------|
| `VPS_HOST` | `ваш_ip_адрес_vps` | IP адрес вашего VPS сервера |
| `VPS_USER` | `ubuntu` или `root` | SSH пользователь на VPS |
| `VPS_PORT` | `22` | SSH порт (обычно 22) |
| `VPS_SSH_KEY` | `содержимое ~/.ssh/id_rsa` | Приватный SSH ключ для подключения |
| `TELEGRAM_BOT_TOKEN` | `ваш_токен_бота` | Токен Telegram Bot API |

### 📝 Как получить SSH ключ:

**На вашем локальном компьютере:**

```bash
# Если ключа еще нет, создайте его
ssh-keygen -t rsa -b 4096 -f ~/.ssh/github_deploy -N ""

# Скопируйте содержимое приватного ключа
cat ~/.ssh/github_deploy
```

**На VPS:**

```bash
# Добавьте публичный ключ
ssh-copy-id -i ~/.ssh/github_deploy.pub root@YOUR_VPS_IP

# Или вручную
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
```

### 🔧 Как получить Telegram Bot Token:

1. Откройте Telegram и найдите `@BotFather`
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен вида: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

## 📋 Шаг 2: Подготовьте VPS

Если у вас еще нет VPS, вот рекомендуемые провайдеры:
- **DigitalOcean** - $5/месяц (рекомендуется)
- **Linode** - $5/месяц
- **Hetzner** - €3/месяц
- **AWS EC2** - free tier

### Минимальные требования:
- **OS:** Ubuntu 22.04
- **RAM:** 2GB
- **CPU:** 1 vCPU
- **Disk:** 20GB SSD

### Инициализация VPS:

```bash
# Подключитесь к VPS
ssh root@YOUR_VPS_IP

# Запустите скрипт инициализации
curl -fsSL https://raw.githubusercontent.com/Pechenje101/FutLive_bot/main/scripts/setup-vps.sh | sudo bash
```

Этот скрипт установит:
- Docker & Docker Compose
- Nginx
- Certbot (для SSL)
- Git
- Node.js & Python

## 🔄 Шаг 3: Проверьте GitHub Actions

1. Откройте: https://github.com/Pechenje101/FutLive_bot/actions
2. Нажмите на последний workflow
3. Проверьте логи

### Успешный деплой должен показать:
```
✅ Build successful
✅ Tests passed
✅ Deployed to VPS
✅ SSL certificate configured
```

## 🧪 Шаг 4: Тестирование

После успешного деплоя:

```bash
# На вашем локальном компьютере
ssh root@YOUR_VPS_IP

# Проверьте статус контейнеров
docker-compose ps

# Проверьте логи
docker-compose logs -f

# Проверьте Web App
curl https://YOUR_DOMAIN/health
```

## 🔐 Шаг 5: Настройка SSL (Let's Encrypt)

Скрипт `setup-vps.sh` уже настраивает SSL автоматически!

Проверьте сертификат:
```bash
sudo certbot certificates
```

Автоматическое обновление:
```bash
sudo systemctl status certbot.timer
```

## 📊 Шаг 6: Мониторинг

### Проверьте Sentry (мониторинг ошибок):

1. Откройте https://sentry.io
2. Создайте аккаунт
3. Создайте новый проект
4. Скопируйте DSN
5. Добавьте в GitHub Secrets: `SENTRY_DSN`

### Проверьте Prometheus (метрики):

```bash
# На VPS
curl http://localhost:9090
```

## 🚀 Шаг 7: Первый Деплой

Теперь при каждом push на main ветку:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

GitHub Actions автоматически:
1. ✅ Запустит тесты
2. ✅ Соберет Docker образы
3. ✅ Загрузит на VPS
4. ✅ Перезагрузит контейнеры
5. ✅ Обновит SSL сертификат

## 📞 Решение проблем

### GitHub Actions не может подключиться к VPS

```bash
# Проверьте SSH ключ
ssh -i ~/.ssh/github_deploy -p YOUR_VPS_PORT ubuntu@YOUR_VPS_IP

# Проверьте GitHub Secrets
# Settings → Secrets → Actions
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

### API не отвечает

```bash
# На VPS
curl http://localhost:5000/api/health
docker-compose logs api
```

## 📚 Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Sentry Documentation](https://docs.sentry.io/)

## ✅ Чек-лист

- [ ] Добавлены все GitHub Secrets
- [ ] VPS инициализирован скриптом `setup-vps.sh`
- [ ] SSH ключ добавлен на VPS
- [ ] GitHub Actions успешно выполнен
- [ ] Web App доступен по HTTPS
- [ ] Telegram Bot работает
- [ ] Sentry мониторит ошибки
- [ ] Prometheus собирает метрики

## 🎉 Готово!

Ваш проект теперь полностью автоматизирован и готов к production!

При каждом push на GitHub:
1. Код автоматически тестируется
2. Docker образы собираются
3. Приложение развертывается на VPS
4. SSL сертификат обновляется

**Вопросы? Смотрите документацию:**
- [GITHUB_DEPLOYMENT.md](./GITHUB_DEPLOYMENT.md)
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- [PRODUCTION_README.md](./PRODUCTION_README.md)
