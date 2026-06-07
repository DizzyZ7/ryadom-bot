import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


async def safe_send_message(bot: Bot, chat_id: int, text: str) -> bool:
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramAPIError as exc:
        logger.warning("Failed to send Telegram message to %s: %s", chat_id, exc)
        return False
