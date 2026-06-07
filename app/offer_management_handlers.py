from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select, update

from app.database import SessionFactory
from app.models import HelpRequest, HelpRequestStatus, Offer, OfferStatus, User
from app.notifications import safe_send_message
from app.repositories import get_or_create_user

offer_management_router = Router()


def user_label(user: User | None) -> str:
    if user is None:
        return "неизвестно"
    if user.username:
        return "@" + user.username
    return user.first_name or str(user.telegram_id)


def user_trust_label(user: User | None) -> str:
    if user is None:
        return "неизвестно"
    verified = "проверен" if user.is_verified else "не проверен"
    return f"{user_label(user)} | рейтинг {user.rating} ({user.rating_count} отзывов) | {verified}"


def offer_keyboard(offer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Принять", callback_data=f"accept_offer:{offer_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"reject_offer:{offer_id}"),
            ]
        ]
    )


@offer_management_router.message(Command("offers"))
@offer_management_router.message(F.text == "Отклики по моим заявкам")
async def owner_offers(message: Message) -> None:
    async with SessionFactory() as session:
        current_user = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        rows = await session.execute(
            select(Offer, HelpRequest, User)
            .join(HelpRequest, HelpRequest.id == Offer.request_id)
            .join(User, User.id == Offer.helper_id)
            .where(HelpRequest.user_id == current_user.id)
            .where(Offer.status == OfferStatus.PENDING.value)
            .order_by(Offer.created_at.asc())
            .limit(20)
        )
        items = list(rows.all())

    if not items:
        await message.answer("Новых откликов по твоим заявкам пока нет.")
        return

    for offer, request, helper in items:
        await message.answer(
            f"<b>Отклик #{offer.id}</b>\n"
            f"Заявка: #{request.id} {request.title}\n"
            f"Помощник: {user_trust_label(helper)}\n\n"
            f"{offer.message or 'Без сообщения'}",
            reply_markup=offer_keyboard(offer.id),
        )


@offer_management_router.message(Command("myoffers"))
@offer_management_router.message(F.text == "Мои отклики")
async def helper_offers(message: Message) -> None:
    async with SessionFactory() as session:
        current_user = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        rows = await session.execute(
            select(Offer, HelpRequest)
            .join(HelpRequest, HelpRequest.id == Offer.request_id)
            .where(Offer.helper_id == current_user.id)
            .order_by(Offer.created_at.desc())
            .limit(20)
        )
        items = list(rows.all())

    if not items:
        await message.answer("Ты пока не откликался на заявки.")
        return

    status_labels = {
        OfferStatus.PENDING.value: "ожидает решения",
        OfferStatus.ACCEPTED.value: "принят",
        OfferStatus.REJECTED.value: "отклонен",
        OfferStatus.CANCELED.value: "отменен",
    }
    text_parts = ["<b>Мои отклики</b>"]
    for offer, request in items:
        text_parts.append(
            f"\n#{offer.id} — {status_labels.get(offer.status, offer.status)}\n"
            f"Заявка: #{request.id} {request.title}"
        )
    await message.answer("\n".join(text_parts))


@offer_management_router.callback_query(F.data.startswith("accept_offer:"))
async def accept_offer(callback: CallbackQuery) -> None:
    offer_id = int(callback.data.split(":", 1)[1])

    async with SessionFactory() as session:
        current_user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if current_user is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        row = await session.execute(
            select(Offer, HelpRequest, User)
            .join(HelpRequest, HelpRequest.id == Offer.request_id)
            .join(User, User.id == Offer.helper_id)
            .where(Offer.id == offer_id)
        )
        item = row.one_or_none()
        if item is None:
            await callback.answer("Отклик не найден", show_alert=True)
            return

        offer, request, helper = item
        if request.user_id != current_user.id:
            await callback.answer("Это не твоя заявка", show_alert=True)
            return
        if offer.status != OfferStatus.PENDING.value:
            await callback.answer("Отклик уже обработан", show_alert=True)
            return

        offer.status = OfferStatus.ACCEPTED.value
        request.status = HelpRequestStatus.IN_PROGRESS.value
        await session.execute(
            update(Offer)
            .where(Offer.request_id == request.id)
            .where(Offer.id != offer.id)
            .where(Offer.status == OfferStatus.PENDING.value)
            .values(status=OfferStatus.REJECTED.value)
        )
        await session.commit()

    await callback.message.answer(f"Отклик #{offer_id} принят. Заявка переведена в работу.")
    await safe_send_message(
        callback.bot,
        helper.telegram_id,
        f"Твой отклик по заявке #{request.id} принят. Свяжись с автором заявки через Telegram: {user_label(current_user)}",
    )
    await callback.answer()


@offer_management_router.callback_query(F.data.startswith("reject_offer:"))
async def reject_offer(callback: CallbackQuery) -> None:
    offer_id = int(callback.data.split(":", 1)[1])

    async with SessionFactory() as session:
        current_user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if current_user is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        row = await session.execute(
            select(Offer, HelpRequest, User)
            .join(HelpRequest, HelpRequest.id == Offer.request_id)
            .join(User, User.id == Offer.helper_id)
            .where(Offer.id == offer_id)
        )
        item = row.one_or_none()
        if item is None:
            await callback.answer("Отклик не найден", show_alert=True)
            return

        offer, request, helper = item
        if request.user_id != current_user.id:
            await callback.answer("Это не твоя заявка", show_alert=True)
            return
        if offer.status != OfferStatus.PENDING.value:
            await callback.answer("Отклик уже обработан", show_alert=True)
            return

        offer.status = OfferStatus.REJECTED.value
        await session.commit()

    await callback.message.answer(f"Отклик #{offer_id} отклонен.")
    await safe_send_message(callback.bot, helper.telegram_id, f"Твой отклик по заявке #{request.id} отклонен.")
    await callback.answer()
