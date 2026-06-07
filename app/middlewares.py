import logging
import time
from collections.abc import Awaitable, Callable
from html import escape
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from app.config import settings
from app.database import SessionFactory
from app.models import User

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    def __init__(self, notify_admins: bool = True, cooldown_seconds: float = 30.0) -> None:
        self.notify_admins = notify_admins
        self.cooldown_seconds = cooldown_seconds
        self.last_notification_at = 0.0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            logger.exception("Unhandled update error: %s", exc)
            await self._answer_user(event)
            await self._notify_admins(event, data, exc)
            return None

    async def _answer_user(self, event: TelegramObject) -> None:
        try:
            if isinstance(event, Message):
                await event.answer("Произошла ошибка. Администратор уже сможет посмотреть ее в логах.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Произошла ошибка. Попробуй позже.", show_alert=True)
        except Exception:
            logger.exception("Failed to send user-facing error message")

    async def _notify_admins(self, event: TelegramObject, data: dict[str, Any], exc: Exception) -> None:
        if not self.notify_admins or not settings.admin_ids:
            return

        now = time.monotonic()
        if now - self.last_notification_at < self.cooldown_seconds:
            return
        self.last_notification_at = now

        bot = data.get("bot")
        if not isinstance(bot, Bot):
            return

        user_id = "unknown"
        update_type = type(event).__name__
        if isinstance(event, Message) and event.from_user:
            user_id = str(event.from_user.id)
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = str(event.from_user.id)

        error_text = escape(f"{type(exc).__name__}: {exc}")[:1500]
        text = (
            "<b>Unhandled bot error</b>\n"
            f"Environment: {escape(settings.environment)}\n"
            f"Update: {escape(update_type)}\n"
            f"User: {escape(user_id)}\n\n"
            f"<code>{error_text}</code>"
        )

        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                logger.exception("Failed to notify admin %s about error", admin_id)


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        if from_user is None:
            return await handler(event, data)

        async with SessionFactory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == from_user.id))
            if user and user.is_banned:
                if isinstance(event, Message):
                    await event.answer("Доступ к боту ограничен.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Доступ к боту ограничен.", show_alert=True)
                return None

        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: float) -> None:
        self.limit_seconds = max(0.0, limit_seconds)
        self.last_seen_at: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if self.limit_seconds <= 0:
            return await handler(event, data)

        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        if from_user is None:
            return await handler(event, data)

        now = time.monotonic()
        last_seen_at = self.last_seen_at.get(from_user.id, 0.0)
        if now - last_seen_at < self.limit_seconds:
            if isinstance(event, CallbackQuery):
                await event.answer("Слишком часто. Попробуй чуть позже.", show_alert=False)
            return None

        self.last_seen_at[from_user.id] = now
        return await handler(event, data)
