import asyncio
import logging
from aiohttp import web
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
    BROADCAST_WAIT,
)
from scheduler import payout_reminder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"


async def handle_webhook(request: web.Request):
    app = request.app["bot_app"]
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(status=200)


async def on_startup(app: Application):
    await app.bot.set_webhook(
        url=config.WEBHOOK_URL,
        secret_token=config.WEBHOOK_SECRET or None,
    )
    logger.info(f"Webhook set: {config.WEBHOOK_URL}")


def build_app() -> Application:
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

    jq = application.job_queue
    jq.run_repeating(
        payout_reminder,
        interval=3600,
        first=10,
    )

    application.post_init = on_startup

    return application


async def run_webhook():
    application = build_app()
    await application.initialize()
    await application.start()

    await application.bot.set_webhook(
        url=config.WEBHOOK_URL,
        secret_token=config.WEBHOOK_SECRET or None,
    )

    app = web.Application()
    app["bot_app"] = application
    app.router.add_post(WEBHOOK_PATH, handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Bot started on port 8080")

    stop_event = asyncio.Event()

    def _stop():
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (2, 15):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    await stop_event.wait()

    await application.stop()
    await application.shutdown()
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_webhook())
