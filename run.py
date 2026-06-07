import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.all_handlers import router
from app.config import settings
from app.database import create_db_schema, dispose_engine
from app.middlewares import BanMiddleware, RateLimitMiddleware


async def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if settings.create_schema_on_start:
        await create_db_schema()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.message.middleware(BanMiddleware())
    dispatcher.callback_query.middleware(BanMiddleware())
    dispatcher.message.middleware(RateLimitMiddleware(settings.rate_limit_seconds))
    dispatcher.callback_query.middleware(RateLimitMiddleware(settings.rate_limit_seconds))
    dispatcher.include_router(router)

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
