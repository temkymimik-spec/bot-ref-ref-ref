import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

import config
import database as db
from handlers.user import (
    start, receive_key, dashboard, balance, stats,
    withdraw_start, receive_wallet, receive_network,
    WAIT_KEY, WAIT_WALLET, WAIT_NETWORK,
)
from handlers.admin import (
    admin_panel, admin_callback, admin_text_router,
)
from scheduler import payout_reminder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    db.init_db()

    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAIT_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_key)],
            WAIT_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wallet)],
            WAIT_NETWORK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_network)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv)
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("withdraw", withdraw_start))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^adm_"))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_router)
    )

    application.job_queue.run_repeating(
        payout_reminder,
        interval=3600,
        first=10,
    )

    logger.info("Bot starting with long polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
