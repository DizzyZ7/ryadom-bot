from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select, text

from app.config import settings
from app.database import SessionFactory
from app.models import Complaint, ComplaintStatus, HelpRequest, HelpRequestStatus, Offer, OfferStatus, User

health_router = Router()


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def status_label(ok: bool) -> str:
    return "OK" if ok else "FAIL"


@health_router.message(Command("health"))
async def health_check(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    db_ok = False
    error_text = None
    users_count = 0
    published_requests_count = 0
    moderation_requests_count = 0
    pending_offers_count = 0
    new_complaints_count = 0

    try:
        async with SessionFactory() as session:
            await session.execute(text("select 1"))
            db_ok = True
            users_count = await session.scalar(select(func.count()).select_from(User)) or 0
            published_requests_count = await session.scalar(
                select(func.count())
                .select_from(HelpRequest)
                .where(HelpRequest.status == HelpRequestStatus.PUBLISHED.value)
            ) or 0
            moderation_requests_count = await session.scalar(
                select(func.count())
                .select_from(HelpRequest)
                .where(HelpRequest.status == HelpRequestStatus.MODERATION.value)
            ) or 0
            pending_offers_count = await session.scalar(
                select(func.count())
                .select_from(Offer)
                .where(Offer.status == OfferStatus.PENDING.value)
            ) or 0
            new_complaints_count = await session.scalar(
                select(func.count())
                .select_from(Complaint)
                .where(Complaint.status == ComplaintStatus.NEW.value)
            ) or 0
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"

    admin_ids_count = len(settings.admin_ids)
    config_ok = bool(settings.telegram_bot_token and settings.database_url and admin_ids_count > 0)

    text_parts = [
        "<b>Health check</b>",
        f"Database: {status_label(db_ok)}",
        f"Config: {status_label(config_ok)}",
        f"Environment: {settings.environment}",
        f"Admins configured: {admin_ids_count}",
        f"Create schema on start: {settings.create_schema_on_start}",
        f"Rate limit seconds: {settings.rate_limit_seconds}",
        "",
        "<b>Counters</b>",
        f"Users: {users_count}",
        f"Published requests: {published_requests_count}",
        f"Requests on moderation: {moderation_requests_count}",
        f"Pending offers: {pending_offers_count}",
        f"New complaints: {new_complaints_count}",
    ]
    if error_text:
        text_parts.extend(["", f"Error: {error_text}"])

    await message.answer("\n".join(text_parts))
