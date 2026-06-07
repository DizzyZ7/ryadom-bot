from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from app.config import settings
from app.database import SessionFactory
from app.models import Complaint, ComplaintStatus, HelpRequest, Offer, OfferStatus, Review, User
from aiogram import Router

admin_stats_router = Router()


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def format_rows(rows: list[tuple[str | None, int]], empty_label: str = "не указано") -> str:
    if not rows:
        return "нет данных"
    return "\n".join(f"- {label or empty_label}: {count}" for label, count in rows)


@admin_stats_router.message(Command("stats"))
async def admin_stats(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    async with SessionFactory() as session:
        users_count = await session.scalar(select(func.count()).select_from(User))
        banned_users_count = await session.scalar(
            select(func.count()).select_from(User).where(User.is_banned.is_(True))
        )
        verified_users_count = await session.scalar(
            select(func.count()).select_from(User).where(User.is_verified.is_(True))
        )
        requests_count = await session.scalar(select(func.count()).select_from(HelpRequest))
        offers_count = await session.scalar(select(func.count()).select_from(Offer))
        reviews_count = await session.scalar(select(func.count()).select_from(Review))
        new_complaints_count = await session.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.status == ComplaintStatus.NEW.value)
        )

        request_status_rows = list(
            (
                await session.execute(
                    select(HelpRequest.status, func.count())
                    .group_by(HelpRequest.status)
                    .order_by(func.count().desc())
                )
            ).all()
        )
        offer_status_rows = list(
            (
                await session.execute(
                    select(Offer.status, func.count())
                    .group_by(Offer.status)
                    .order_by(func.count().desc())
                )
            ).all()
        )
        category_rows = list(
            (
                await session.execute(
                    select(HelpRequest.category, func.count())
                    .group_by(HelpRequest.category)
                    .order_by(func.count().desc())
                    .limit(10)
                )
            ).all()
        )
        city_rows = list(
            (
                await session.execute(
                    select(HelpRequest.city, func.count())
                    .group_by(HelpRequest.city)
                    .order_by(func.count().desc())
                    .limit(10)
                )
            ).all()
        )
        top_users_rows = list(
            (
                await session.execute(
                    select(User.telegram_id, User.username, User.rating_sum, User.rating_count)
                    .where(User.rating_count > 0)
                    .order_by((User.rating_sum / User.rating_count).desc(), User.rating_count.desc())
                    .limit(10)
                )
            ).all()
        )

    top_users = []
    for telegram_id, username, rating_sum, rating_count in top_users_rows:
        rating = round(rating_sum / rating_count, 2) if rating_count else 0
        label = f"@{username}" if username else str(telegram_id)
        top_users.append(f"- {label}: {rating} ({rating_count} отзывов)")

    await message.answer(
        "<b>Статистика Ryadom Bot</b>\n\n"
        f"Пользователей: {users_count or 0}\n"
        f"Проверенных: {verified_users_count or 0}\n"
        f"Забаненных: {banned_users_count or 0}\n"
        f"Заявок: {requests_count or 0}\n"
        f"Откликов: {offers_count or 0}\n"
        f"Отзывов: {reviews_count or 0}\n"
        f"Новых жалоб: {new_complaints_count or 0}\n\n"
        "<b>Заявки по статусам</b>\n"
        f"{format_rows(request_status_rows)}\n\n"
        "<b>Отклики по статусам</b>\n"
        f"{format_rows(offer_status_rows)}\n\n"
        "<b>Топ категорий</b>\n"
        f"{format_rows(category_rows)}\n\n"
        "<b>Топ городов</b>\n"
        f"{format_rows(city_rows)}\n\n"
        "<b>Топ пользователей по рейтингу</b>\n"
        f"{chr(10).join(top_users) if top_users else 'нет данных'}"
    )
