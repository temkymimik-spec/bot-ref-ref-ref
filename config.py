import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.botherost.ru/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
LEAD_PRICE = float(os.getenv("LEAD_PRICE", "0.5"))
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
PAYMENT_NOTIFY_HOUR = int(os.getenv("PAYMENT_NOTIFY_HOUR", "19"))
