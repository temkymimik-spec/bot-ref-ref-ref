import datetime
from telegram.ext import ContextTypes
import database as db
import config


async def payout_reminder(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    weekday = now.weekday()

    if weekday not in (4, 5, 6):
        return

    if now.hour != config.PAYMENT_NOTIFY_HOUR:
        return

    users = db.get_all_active_users()
    for uid in users:
        u = db.get_user(uid)
        if not u or u["balance"] <= 0:
            continue

        try:
            await context.bot.send_message(
                uid,
                "📢 <b>Внимание!</b>\n\n"
                "💸 Период выплат открыт!\n"
                f"💰 Ваш баланс: <b>{u['balance']:.2f} руб.</b>\n\n"
                "Нажмите /start и подайте заявку на вывод!",
                parse_mode="HTML",
            )
        except Exception:
            pass
