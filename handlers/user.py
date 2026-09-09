from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
import database as db
import config

WAIT_KEY, WAIT_WALLET, WAIT_NETWORK = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, None)

    db_user = db.get_user(user.id)
    if db_user and db_user["is_active"]:
        await show_dashboard(update, context)
        return ConversationHandler.END

    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Для доступа к боту введи ключ активации.\n"
        "Получить ключ можно у администратора.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAIT_KEY


async def receive_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    user = update.effective_user

    if not db.is_key_valid(key):
        await update.message.reply_text("❌ Неверный или использованный ключ.\nПопробуйте ещё раз:")
        return WAIT_KEY

    db.add_user(user.id, user.username, user.first_name, key)
    db.use_key(key, user.id)
    db.activate_user(user.id)

    await update.message.reply_text(
        "✅ Ключ принят! Добро пожаловать!",
    )
    await show_dashboard(update, context)
    return ConversationHandler.END


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = db.get_user(update.effective_user.id)
    if not db_user or not db_user["is_active"]:
        await update.message.reply_text("⛔ Доступ неактивен. Используйте /start")
        return
    await show_dashboard(update, context)


async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = db.get_user(update.effective_user.id)
    if not db_user:
        return

    kb = ReplyKeyboardMarkup(
        [["💰 Мой баланс"], ["📝 Вывод средств"], ["📊 Статистика"]],
        resize_keyboard=True,
    )

    text = (
        f"📊 <b>Ваш кабинет</b>\n\n"
        f"👤 Пользователь: @{db_user['username'] or update.effective_user.first_name}\n"
        f"🆔 ID: <code>{db_user['user_id']}</code>\n\n"
        f"📥 Лидов: <b>{db_user['leads']}</b>\n"
        f"💰 Баланс: <b>{db_user['balance']:.2f} руб.</b>\n"
        f"✅ Выплачено: <b>{db_user['paid_out']:.2f} руб.</b>\n"
    )

    if hasattr(update, "message") and update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = db.get_user(update.effective_user.id)
    if not db_user or not db_user["is_active"]:
        return

    text = (
        f"💰 <b>Финансы</b>\n\n"
        f"📥 Лидов: <b>{db_user['leads']}</b>\n"
        f"💵 К заработку: <b>{db_user['total_earned']:.2f} руб.</b>\n"
        f"💳 Доступно: <b>{db_user['balance']:.2f} руб.</b>\n"
        f"✅ Выплачено: <b>{db_user['paid_out']:.2f} руб.</b>\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = db.get_user(update.effective_user.id)
    if not db_user or not db_user["is_active"]:
        return

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📥 Всего лидов: <b>{db_user['leads']}</b>\n"
        f"💰 Общий заработок: <b>{db_user['total_earned']:.2f} руб.</b>\n"
        f"💳 Баланс: <b>{db_user['balance']:.2f} руб.</b>\n"
        f"✅ Выплачено: <b>{db_user['paid_out']:.2f} руб.</b>\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = db.get_user(update.effective_user.id)
    if not db_user or not db_user["is_active"]:
        return

    if db_user["balance"] <= 0:
        await update.message.reply_text("❌ Недостаточно средств для вывода.")
        return

    if db.has_pending_withdrawal(update.effective_user.id):
        await update.message.reply_text(
            "⏳ У вас уже есть заявка на вывод. Дождитесь её обработки."
        )
        return

    context.user_data["withdraw_amount"] = db_user["balance"]
    await update.message.reply_text(
        f"💰 Сумма вывода: <b>{db_user['balance']:.2f} руб.</b>\n\n"
        "Введите адрес вашего криптокошелька:",
        parse_mode="HTML",
    )
    return WAIT_WALLET


async def receive_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wallet_address"] = update.message.text.strip()
    await update.message.reply_text(
        "🔗 Выберите сеть для вывода:\n\n"
        "Отправьте одним сообщением:\n"
        "• TRC20\n• ERC20\n• BEP20\n• TON\n• BTC\n• Другая (укажите)",
    )
    return WAIT_NETWORK


async def receive_network(update: Update, context: ContextTypes.DEFAULT_TYPE):
    network = update.message.text.strip().upper()
    user_id = update.effective_user.id
    amount = context.user_data["withdraw_amount"]
    wallet = context.user_data["wallet_address"]

    withdrawal_id = db.create_withdrawal(user_id, amount, wallet, network)

    await update.message.reply_text(
        f"✅ <b>Заявка на вывод создана!</b>\n\n"
        f"🆔 Заявка: #{withdrawal_id}\n"
        f"💰 Сумма: {amount:.2f} руб.\n"
        f"🔗 Сеть: {network}\n"
        f"📧 Адрес: <code>{wallet}</code>\n\n"
        "Ожидайте обработки администратором.",
        parse_mode="HTML",
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"💸 <b>Новая заявка на вывод #{withdrawal_id}</b>\n\n"
                f"👤 @{update.effective_user.username or update.effective_user.first_name} "
                f"(ID: <code>{user_id}</code>)\n"
                f"💰 Сумма: {amount:.2f} руб.\n"
                f"🔗 Сеть: {network}\n"
                f"📧 Адрес: <code>{wallet}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    return ConversationHandler.END
