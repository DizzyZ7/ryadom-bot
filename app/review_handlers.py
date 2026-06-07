from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.database import SessionFactory
from app.models import HelpRequest, HelpRequestStatus, Offer, OfferStatus, Review, User
from app.notifications import safe_send_message

review_router = Router()


def rating_keyboard(request_id: int, target_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data=f"rate:{request_id}:{target_user_id}:1"),
                InlineKeyboardButton(text="2", callback_data=f"rate:{request_id}:{target_user_id}:2"),
                InlineKeyboardButton(text="3", callback_data=f"rate:{request_id}:{target_user_id}:3"),
                InlineKeyboardButton(text="4", callback_data=f"rate:{request_id}:{target_user_id}:4"),
                InlineKeyboardButton(text="5", callback_data=f"rate:{request_id}:{target_user_id}:5"),
            ]
        ]
    )


@review_router.callback_query(F.data.startswith("rate:"))
async def save_rating(callback: CallbackQuery) -> None:
    _, request_id_raw, target_user_id_raw, rating_raw = callback.data.split(":", 3)
    request_id = int(request_id_raw)
    target_user_id = int(target_user_id_raw)
    rating = int(rating_raw)

    if rating < 1 or rating > 5:
        await callback.answer("Некорректная оценка", show_alert=True)
        return

    async with SessionFactory() as session:
        reviewer = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if reviewer is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        request = await session.get(HelpRequest, request_id)
        if request is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        if request.user_id != reviewer.id:
            await callback.answer("Оценивать может только автор заявки", show_alert=True)
            return
        if request.status != HelpRequestStatus.DONE.value:
            await callback.answer("Оценка доступна только после завершения заявки", show_alert=True)
            return

        target = await session.get(User, target_user_id)
        if target is None:
            await callback.answer("Пользователь для оценки не найден", show_alert=True)
            return

        accepted_offer = await session.scalar(
            select(Offer).where(
                Offer.request_id == request.id,
                Offer.helper_id == target.id,
                Offer.status == OfferStatus.ACCEPTED.value,
            )
        )
        if accepted_offer is None:
            await callback.answer("Этого помощника нельзя оценить по заявке", show_alert=True)
            return

        existing_review = await session.scalar(
            select(Review).where(
                Review.request_id == request.id,
                Review.reviewer_id == reviewer.id,
                Review.target_user_id == target.id,
            )
        )
        if existing_review is not None:
            await callback.answer("Оценка уже была оставлена", show_alert=True)
            return

        review = Review(
            request_id=request.id,
            reviewer_id=reviewer.id,
            target_user_id=target.id,
            rating=rating,
        )
        target.rating_sum += rating
        target.rating_count += 1
        session.add(review)
        await session.commit()
        new_rating = target.rating
        target_telegram_id = target.telegram_id

    await callback.message.answer(f"Спасибо. Оценка {rating}/5 сохранена.")
    await safe_send_message(
        callback.bot,
        target_telegram_id,
        f"Тебе поставили оценку {rating}/5 по заявке #{request_id}. Текущий рейтинг: {new_rating}",
    )
    await callback.answer()
