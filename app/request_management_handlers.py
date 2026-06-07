from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.database import SessionFactory
from app.keyboards import URGENCY_TYPES
from app.models import HelpRequest, HelpRequestStatus, Offer, OfferStatus, User
from app.notifications import safe_send_message
from app.review_handlers import rating_keyboard

request_management_router = Router()
URGENCY_LABELS = dict(URGENCY_TYPES)

STATUS_LABELS = {
    HelpRequestStatus.MODERATION.value: "На модерации",
    HelpRequestStatus.PUBLISHED.value: "Опубликована",
    HelpRequestStatus.IN_PROGRESS.value: "В работе",
    HelpRequestStatus.DONE.value: "Выполнена",
    HelpRequestStatus.CANCELED.value: "Отменена",
    HelpRequestStatus.REJECTED.value: "Отклонена",
}


def request_owner_keyboard(request: HelpRequest) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if request.status in {HelpRequestStatus.PUBLISHED.value, HelpRequestStatus.IN_PROGRESS.value}:
        buttons.append([
            InlineKeyboardButton(text="Завершить", callback_data=f"request_done:{request.id}"),
            InlineKeyboardButton(text="Отменить", callback_data=f"request_cancel:{request.id}"),
        ])

    if request.status in {HelpRequestStatus.CANCELED.value, HelpRequestStatus.REJECTED.value, HelpRequestStatus.DONE.value}:
        buttons.append([
            InlineKeyboardButton(text="Вернуть в публикацию", callback_data=f"request_publish:{request.id}"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_request_card(request: HelpRequest, owner: User | None) -> str:
    owner_text = "неизвестно"
    if owner:
        owner_text = "@" + owner.username if owner.username else owner.first_name or str(owner.telegram_id)
    location = ", ".join(item for item in [request.city, request.district] if item) or "не указано"
    urgency = URGENCY_LABELS.get(getattr(request, "urgency", "flexible"), "Не срочно")
    return (
        f"<b>Заявка #{request.id}</b>\n"
        f"Статус: {STATUS_LABELS.get(request.status, request.status)}\n"
        f"Срочность: {urgency}\n"
        f"Автор: {owner_text}\n"
        f"Район: {location}\n"
        f"Когда: {request.needed_at_text or 'не указано'}\n\n"
        f"<b>{request.title}</b>\n"
        f"{request.description}"
    )


@request_management_router.message(Command("request"))
async def show_request(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /request id_заявки")
        return

    request_id = int(args[1].strip())

    async with SessionFactory() as session:
        row = await session.execute(
            select(HelpRequest, User)
            .join(User, User.id == HelpRequest.user_id)
            .where(HelpRequest.id == request_id)
        )
        item = row.one_or_none()

    if item is None:
        await message.answer("Заявка не найдена.")
        return

    request, owner = item
    if owner.telegram_id == message.from_user.id:
        await message.answer(format_request_card(request, owner), reply_markup=request_owner_keyboard(request))
        return

    if request.status != HelpRequestStatus.PUBLISHED.value:
        await message.answer("Эта заявка сейчас недоступна.")
        return

    await message.answer(format_request_card(request, owner))


@request_management_router.callback_query(F.data.startswith("request_done:"))
async def mark_request_done(callback: CallbackQuery) -> None:
    request_id = int(callback.data.split(":", 1)[1])
    helper_id: int | None = None
    helper_telegram_id: int | None = None

    async with SessionFactory() as session:
        row = await session.execute(
            select(HelpRequest, User)
            .join(User, User.id == HelpRequest.user_id)
            .where(HelpRequest.id == request_id)
        )
        item = row.one_or_none()
        if item is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        request, owner = item
        if owner.telegram_id != callback.from_user.id:
            await callback.answer("Это не твоя заявка", show_alert=True)
            return

        if request.status not in {HelpRequestStatus.PUBLISHED.value, HelpRequestStatus.IN_PROGRESS.value}:
            await callback.answer("Этот статус нельзя завершить", show_alert=True)
            return

        accepted_row = await session.execute(
            select(Offer, User)
            .join(User, User.id == Offer.helper_id)
            .where(Offer.request_id == request.id)
            .where(Offer.status == OfferStatus.ACCEPTED.value)
        )
        accepted_item = accepted_row.one_or_none()
        if accepted_item:
            accepted_offer, helper = accepted_item
            helper_id = helper.id
            helper_telegram_id = helper.telegram_id

        request.status = HelpRequestStatus.DONE.value
        await session.commit()

    await callback.message.answer(f"Заявка #{request_id} отмечена как выполненная.")

    if helper_id:
        await callback.message.answer(
            "Оцени помощника по этой заявке от 1 до 5.",
            reply_markup=rating_keyboard(request_id, helper_id),
        )
    if helper_telegram_id:
        await safe_send_message(callback.bot, helper_telegram_id, f"Заявка #{request_id} отмечена как выполненная.")

    await callback.answer()


@request_management_router.callback_query(F.data.startswith("request_cancel:"))
async def cancel_request(callback: CallbackQuery) -> None:
    request_id = int(callback.data.split(":", 1)[1])

    async with SessionFactory() as session:
        row = await session.execute(
            select(HelpRequest, User)
            .join(User, User.id == HelpRequest.user_id)
            .where(HelpRequest.id == request_id)
        )
        item = row.one_or_none()
        if item is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        request, owner = item
        if owner.telegram_id != callback.from_user.id:
            await callback.answer("Это не твоя заявка", show_alert=True)
            return

        if request.status in {HelpRequestStatus.DONE.value, HelpRequestStatus.CANCELED.value}:
            await callback.answer("Заявка уже закрыта", show_alert=True)
            return

        request.status = HelpRequestStatus.CANCELED.value
        offers = await session.scalars(select(Offer).where(Offer.request_id == request.id))
        for offer in offers:
            if offer.status == OfferStatus.PENDING.value:
                offer.status = OfferStatus.CANCELED.value
        await session.commit()

    await callback.message.answer(f"Заявка #{request_id} отменена.")
    await callback.answer()


@request_management_router.callback_query(F.data.startswith("request_publish:"))
async def republish_request(callback: CallbackQuery) -> None:
    request_id = int(callback.data.split(":", 1)[1])

    async with SessionFactory() as session:
        row = await session.execute(
            select(HelpRequest, User)
            .join(User, User.id == HelpRequest.user_id)
            .where(HelpRequest.id == request_id)
        )
        item = row.one_or_none()
        if item is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        request, owner = item
        if owner.telegram_id != callback.from_user.id:
            await callback.answer("Это не твоя заявка", show_alert=True)
            return

        request.status = HelpRequestStatus.PUBLISHED.value
        await session.commit()

    await callback.message.answer(f"Заявка #{request_id} снова опубликована.")
    await callback.answer()
