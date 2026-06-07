from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from app.database import SessionFactory
from app.models import HelpRequest, HelpRequestStatus, Offer, OfferStatus, Review, User

me_router = Router()


@me_router.message(Command("me"))
async def show_me(message: Message) -> None:
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if user is None:
            await message.answer("Профиль пока не создан. Нажми /start.")
            return
        created_count = await session.scalar(select(func.count()).select_from(HelpRequest).where(HelpRequest.user_id == user.id))
        done_count = await session.scalar(
            select(func.count()).select_from(HelpRequest).where(HelpRequest.user_id == user.id).where(HelpRequest.status == HelpRequestStatus.DONE.value)
        )
        accepted_count = await session.scalar(
            select(func.count()).select_from(Offer).where(Offer.helper_id == user.id).where(Offer.status == OfferStatus.ACCEPTED.value)
        )
        reviews_count = await session.scalar(select(func.count()).select_from(Review).where(Review.target_user_id == user.id))

    if user.is_banned:
        await message.answer("Профиль недоступен.")
        return

    name = "@" + user.username if user.username else user.first_name or str(user.telegram_id)
    location = ", ".join(item for item in [user.city, user.district] if item) or "не указано"
    await message.answer(
        f"<b>Мой профиль: {name}</b>\n\n"
        f"Локация: {location}\n"
        f"Проверен: {'да' if user.is_verified else 'нет'}\n"
        f"Рейтинг: {user.rating} ({reviews_count or 0} отзывов)\n\n"
        f"Создано заявок: {created_count or 0}\n"
        f"Завершено своих заявок: {done_count or 0}\n"
        f"Принятых откликов как помощник: {accepted_count or 0}"
    )
