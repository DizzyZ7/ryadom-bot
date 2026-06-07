from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.config import settings
from app.database import SessionFactory
from app.models import ModerationLog, User

admin_audit_router = Router()


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def moderator_label(user: User | None) -> str:
    if user is None:
        return "unknown"
    if user.username:
        return "@" + user.username
    return str(user.telegram_id)


@admin_audit_router.message(Command("audit"))
async def audit_log(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    limit = 10
    if len(args) > 1 and args[1].strip().isdigit():
        limit = min(max(int(args[1].strip()), 1), 30)

    async with SessionFactory() as session:
        rows = await session.execute(
            select(ModerationLog, User)
            .outerjoin(User, User.id == ModerationLog.moderator_id)
            .order_by(ModerationLog.created_at.desc())
            .limit(limit)
        )
        items = list(rows.all())

    if not items:
        await message.answer("Журнал аудита пуст.")
        return

    parts = ["<b>Журнал действий</b>"]
    for log, moderator in items:
        entity = log.entity_type
        if log.entity_id is not None:
            entity += f" #{log.entity_id}"
        details = f"\n{log.details}" if log.details else ""
        parts.append(
            f"\n<b>{log.action}</b>\n"
            f"Модератор: {moderator_label(moderator)}\n"
            f"Объект: {entity}\n"
            f"Время: {log.created_at}{details}"
        )

    await message.answer("\n".join(parts))
