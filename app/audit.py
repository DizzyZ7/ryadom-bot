from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModerationLog, User


async def write_audit_log(
    session: AsyncSession,
    moderator_telegram_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str | None = None,
) -> None:
    moderator = await session.scalar(select(User).where(User.telegram_id == moderator_telegram_id))
    log = ModerationLog(
        moderator_id=moderator.id if moderator else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    session.add(log)
