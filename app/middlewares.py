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
