from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import database as db
import config
from utils import is_admin

BROADCAST_WAIT = 100


def admin_check(update: Update) -> bool:
    uid = update.effective_user.id
    if not is_admin(uid):
        if hasattr(update, "callback_query") and update.callback_query:
            update.callback_query.answer("⛔ Нет доступа", show_alert=True)
        return False
    return True


# ─── ADMIN PANEL ──────────────────────────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_check(update):
        return
    stats = db.get_total_stats()
    total_users = stats.get("total_users", 0) or 0
    total_leads = stats.get("total_leads", 0) or 0
    total_earned = stats.get("total_earned", 0) or 0
    total_paid = stats.get("total_paid", 0) or 0
    pending = len(db.get_pending_withdrawals())

    text = (
        "🔧 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📥 Всего лидов: {total_leads}\n"
        f"💰 Заработано: {total_earned:.2f} руб.\n"
        f"✅ Выплачено: {total_paid:.2f} руб.\n"
        f"⏳ Заявок на вывод: {pending}\n"
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👥 Пользователи", callback_data="adm_users")],
            [
                InlineKeyboardButton("💸 Заявки на вывод", callback_data="adm_withdrawals"),
                InlineKeyboardButton("🔑 Ключи", callback_data="adm_keys"),
            ],
            [
                InlineKeyboardButton("📋 Рассылка", callback_data="adm_broadcast"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="adm_settings"),
            ],
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="adm_panel"),
            ],
        ]
    )

    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_check(update):
        return
    q = update.callback_query
    data = q.data

    if data == "adm_panel":
        await admin_panel(update, context)
    elif data == "adm_users":
        await show_users(update, context)
    elif data.startswith("adm_user_"):
        uid = int(data.split("_")[2])
        await show_user(update, context, uid)
    elif data.startswith("adm_setleads_"):
        uid = int(data.split("_")[2])
        context.user_data["set_leads_target"] = uid
        await q.edit_message_text("Введите количество лидов:")
        context.user_data["admin_state"] = "wait_leads"
    elif data.startswith("adm_setbal_"):
        uid = int(data.split("_")[2])
        context.user_data["set_bal_target"] = uid
        await q.edit_message_text("Введите сумму баланса:")
        context.user_data["admin_state"] = "wait_balance"
    elif data.startswith("adm_setpaid_"):
        uid = int(data.split("_")[2])
        context.user_data["set_paid_target"] = uid
        await q.edit_message_text("Введите сумму выплат:")
        context.user_data["admin_state"] = "wait_paid"
    elif data.startswith("adm_addleads_"):
        uid = int(data.split("_")[2])
        context.user_data["add_leads_target"] = uid
        await q.edit_message_text("Введите сколько лидов добавить:")
        context.user_data["admin_state"] = "wait_add_leads"
    elif data.startswith("adm_rmuser_"):
        uid = int(data.split("_")[2])
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Да, удалить", callback_data=f"adm_rmuser_yes_{uid}"),
                    InlineKeyboardButton("❌ Отмена", callback_data=f"adm_user_{uid}"),
                ]
            ]
        )
        await q.edit_message_text(f"Удалить пользователя {uid}?", reply_markup=keyboard)
    elif data.startswith("adm_rmuser_yes_"):
        uid = int(data.split("_")[3])
        db.remove_user(uid)
        await q.edit_message_text(f"✅ Пользователь {uid} удалён.")
    elif data == "adm_withdrawals":
        await show_withdrawals(update, context)
    elif data.startswith("adm_appwith_"):
        wid = int(data.split("_")[2])
        await process_withdrawal(update, context, wid, approve=True)
    elif data.startswith("adm_rejwith_"):
        wid = int(data.split("_")[2])
        await process_withdrawal(update, context, wid, approve=False)
    elif data == "adm_keys":
        await show_keys(update, context)
    elif data.startswith("adm_genkey"):
        await generate_keys(update, context)
    elif data.startswith("adm_delkey_"):
        key = data.replace("adm_delkey_", "")
        db.delete_key(key)
        await show_keys(update, context)
    elif data == "adm_broadcast":
        context.user_data["admin_state"] = "wait_broadcast"
        await q.edit_message_text("📝 Введите текст рассылки (или /cancel для отмены):")
    elif data == "adm_settings":
        await show_settings(update, context)


# ─── USERS MANAGEMENT ────────────────────────────────────────
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_users()
    text = f"👥 <b>Пользователи ({len(users)})</b>\n\n"
    buttons = []
    row = []
    for i, u in enumerate(users[:20]):
        status = "✅" if u["is_active"] else "❌"
        name = f"@{u['username']}" if u["username"] else u["first_name"] or str(u["user_id"])
        row.append(InlineKeyboardButton(f"{status} {name}", callback_data=f"adm_user_{u['user_id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="adm_panel")])
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def show_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    u = db.get_user(user_id)
    if not u:
        await update.callback_query.edit_message_text("❌ Пользователь не найден.")
        return

    name = f"@{u['username']}" if u["username"] else u["first_name"] or "—"
    status = "✅ Активен" if u["is_active"] else "❌ Неактивен"
    text = (
        f"👤 <b>Пользователь</b>\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"📛 Имя: {name}\n"
        f"📌 Статус: {status}\n"
        f"🔑 Ключ: <code>{u['access_key'] or '—'}</code>\n\n"
        f"📥 Лидов: <b>{u['leads']}</b>\n"
        f"💰 Заработано: <b>{u['total_earned']:.2f} руб.</b>\n"
        f"💳 Баланс: <b>{u['balance']:.2f} руб.</b>\n"
        f"✅ Выплачено: <b>{u['paid_out']:.2f} руб.</b>\n"
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📥 Установить лиды", callback_data=f"adm_setleads_{user_id}")],
            [InlineKeyboardButton("➕ Добавить лиды", callback_data=f"adm_addleads_{user_id}")],
            [InlineKeyboardButton("💳 Установить баланс", callback_data=f"adm_setbal_{user_id}")],
            [InlineKeyboardButton("✅ Установить выплаты", callback_data=f"adm_setpaid_{user_id}")],
            [InlineKeyboardButton("❌ Удалить", callback_data=f"adm_rmuser_{user_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="adm_users")],
        ]
    )
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ─── WITHDRAWALS ──────────────────────────────────────────────
async def show_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wds = db.get_pending_withdrawals()
    if not wds:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="adm_panel")]])
        await update.callback_query.edit_message_text("✅ Нет заявок на вывод.", reply_markup=kb)
        return

    text = f"💸 <b>Заявки на вывод ({len(wds)})</b>\n\n"
    for w in wds[:10]:
        text += (
            f"🆔 #{w['id']} | 👤 {w['user_id']}\n"
            f"💰 {w['amount']:.2f} руб. | 🔗 {w['network']}\n"
            f"📧 <code>{w['address']}</code>\n\n"
        )

    buttons = []
    for w in wds[:10]:
        buttons.append(
            [
                InlineKeyboardButton(f"✅ #{w['id']}", callback_data=f"adm_appwith_{w['id']}"),
                InlineKeyboardButton(f"❌ #{w['id']}", callback_data=f"adm_rejwith_{w['id']}"),
            ]
        )
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="adm_panel")])

    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, withdrawal_id: int, approve: bool):
    if approve:
        result = db.approve_withdrawal(withdrawal_id)
        if not result:
            await update.callback_query.edit_message_text("❌ Заявка не найдена.")
            return
        try:
            await context.bot.send_message(
                result["user_id"],
                f"✅ Заявка #{withdrawal_id} одобрена!\n"
                f"💰 {result['amount']:.2f} руб. будет переведено на {result['network']} "
                f"адрес <code>{result['address']}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await show_withdrawals(update, context)
    else:
        result = db.reject_withdrawal(withdrawal_id)
        if not result:
            await update.callback_query.edit_message_text("❌ Заявка не найдена.")
            return
        try:
            await context.bot.send_message(
                result["user_id"],
                f"❌ Заявка #{withdrawal_id} отклонена.\n💰 Средства возвращены на баланс.",
            )
        except Exception:
            pass
        await show_withdrawals(update, context)


# ─── KEYS ─────────────────────────────────────────────────────
async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = db.get_all_keys()
    unused = [k for k in keys if k["used_by"] is None]

    text = f"🔑 <b>Ключи</b> (всего: {len(keys)}, свободных: {len(unused)})\n\n"
    for k in keys[:15]:
        status = "🟢" if k["used_by"] is None else f"🔴 → {k['used_by']}"
        text += f"<code>{k['key']}</code> {status}\n"

    kb = [
        [
            InlineKeyboardButton("➕ Сгенерировать", callback_data="adm_genkey"),
        ]
    ]
    for k in unused[:10]:
        kb.append([InlineKeyboardButton(f"🗑 {k['key']}", callback_data=f"adm_delkey_{k['key']}")])
    kb.append([InlineKeyboardButton("🔙 Назад", callback_data="adm_panel")])

    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


async def generate_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import secrets
    keys = []
    for _ in range(5):
        key = f"KEY-{secrets.token_hex(6).upper()}"
        db.add_key(key)
        keys.append(key)

    text = "🔑 <b>Сгенерировано 5 ключей:</b>\n\n" + "\n".join(f"<code>{k}</code>" for k in keys)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К ключам", callback_data="adm_keys")]])
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ─── SETTINGS ─────────────────────────────────────────────────
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"💰 Цена лида: <b>{config.LEAD_PRICE} руб.</b>\n"
        f"⏰ Уведомления: <b>пятница-воскресенье {config.PAYMENT_NOTIFY_HOUR}:00</b>\n"
        f"🆔 Админы: <code>{config.ADMIN_IDS}</code>\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="adm_panel")]])
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ─── BROADCAST ────────────────────────────────────────────────
async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_check(update):
        return ConversationHandler.END

    text = update.message.text
    users = db.get_all_active_users()
    sent, failed = 0, 0
    for uid in users:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"📨 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}"
    )
    return ConversationHandler.END


# ─── TEXT ROUTER (admin state machine) ────────────────────────
async def admin_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_check(update):
        return

    state = context.user_data.get("admin_state")
    text = update.message.text.strip()

    if state == "wait_leads":
        uid = context.user_data.get("set_leads_target")
        try:
            val = int(text)
            db.set_leads(uid, val)
            await update.message.reply_text(f"✅ Установлено {val} лидов для {uid}.")
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        context.user_data["admin_state"] = None

    elif state == "wait_balance":
        uid = context.user_data.get("set_bal_target")
        try:
            val = float(text)
            db.set_balance(uid, val)
            await update.message.reply_text(f"✅ Баланс {uid} = {val:.2f} руб.")
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        context.user_data["admin_state"] = None

    elif state == "wait_paid":
        uid = context.user_data.get("set_paid_target")
        try:
            val = float(text)
            db.set_paid_out(uid, val)
            await update.message.reply_text(f"✅ Выплаты {uid} = {val:.2f} руб.")
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        context.user_data["admin_state"] = None

    elif state == "wait_add_leads":
        uid = context.user_data.get("add_leads_target")
        try:
            val = int(text)
            db.add_leads(uid, val)
            u = db.get_user(uid)
            await update.message.reply_text(f"✅ Добавлено {val} лидов. Теперь у {uid}: {u['leads']} лидов.")
        except ValueError:
            await update.message.reply_text("❌ Введите число.")
        context.user_data["admin_state"] = None

    elif state == "wait_broadcast":
        await receive_broadcast(update, context)
        context.user_data["admin_state"] = None
