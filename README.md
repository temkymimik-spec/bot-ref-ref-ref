# Telegram Bot — Lead Tracking & Payouts

## Деплой на BotHost.ru

1. Зарегистрируйтесь на [BotHost.ru](https://botherost.ru)
2. Создайте проект, выберите Python
3. Загрузите все файлы из этой папки
4. В настройках проекта заполните переменные окружения:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | Ваш Telegram ID (через запятую если несколько) |
| `WEBHOOK_URL` | URL вашего проекта + `/webhook` (выдаёт BotHost) |
| `WEBHOOK_SECRET` | Секретный токен (可以在 BotHost настройках) |
| `LEAD_PRICE` | Цена одного лида в рублях (по умолчанию 0.5) |
| `PAYMENT_NOTIFY_HOUR` | Час отправки уведомлений (по умолчанию 19) |

5. Запустите проект

## Команды

### Пользователь
- `/start` — Вход / регистрация по ключу
- `/dashboard` — Кабинет
- `/balance` — Финансы
- `/stats` — Статистика
- `/withdraw` — Заявка на вывод

### Админ
- `/admin` — Админ-панель

## Доступные переменные окружения

```
BOT_TOKEN=...
ADMIN_IDS=...
WEBHOOK_URL=...
WEBHOOK_SECRET=...
LEAD_PRICE=0.5
PAYMENT_NOTIFY_HOUR=19
DB_PATH=bot_data.db
```
