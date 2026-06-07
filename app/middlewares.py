import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from app.database import SessionFactory
from app.models import User


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
