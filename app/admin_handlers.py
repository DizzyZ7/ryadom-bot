from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from app.config import settings
from app.database import SessionFactory
from app.models import Complaint, ComplaintStatus, HelpRequest, HelpRequestStatus, User

admin_router = Router()

STATUS_LABELS = {
    "moderation": "На модерации",
    "published": "Опубликована",
    "in_progress": "В работе",
    "done": "Выполнена",
    "canceled": "Отменена",
    "rejected": "Отклонена",
}


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def admin_request_text(request: HelpRequest, owner: User | None) -> str:
    owner_text = "неизвестно"
    if owner:
        owner_text = f"{owner.telegram_id}"
        if owner.username:
            owner_text += f" / @{owner.username}"
    location = ", ".join(item for item in [request.city, request.district] if item) or "не указано"
    return (
        f"<b>Заявка #{request.id}</b>\n"
        f"Статус: {STATUS_LABELS.get(request.status, request.status)}\n"
        f"Автор: {owner_text}\n"
        f"Категория: {request.category}\n"
        f"Локация: {location}\n"
        f"Когда: {request.needed_at_text or 'не указано'}\n\n"
        f"<b>{request.title}</b>\n"
        f"{request.description}"
    )


def moderation_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Опубликовать", callback_data=f"admin:publish:{request_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"admin:reject:{request_id}"),
            ]
        ]
    )


@admin_router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    async with SessionFactory() as session:
        moderation_count = await session.scalar(
            select(func.count()).select_from(HelpRequest).where(HelpRequest.status == HelpRequestStatus.MODERATION.value)
        )
        complaints_count = await session.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.status == ComplaintStatus.NEW.value)
        )
        users_count = await session.scalar(select(func.count()).select_from(User))
        requests_count = await session.scalar(select(func.count()).select_from(HelpRequest))

    await message.answer(
        "<b>Админ-панель</b>\n\n"
        f"Пользователей: {users_count or 0}\n"
        f"Заявок всего: {requests_count or 0}\n"
        f"На модерации: {moderation_count or 0}\n"
        f"Новых жалоб: {complaints_count or 0}\n\n"
        "Команды:\n"
        "/moderation — заявки на модерации\n"
        "/complaints — новые жалобы"
    )


@admin_router.message(Command("moderation"))
async def moderation_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    async with SessionFactory() as session:
        rows = await session.execute(
            select(HelpRequest, User)
            .join(User, User.id == HelpRequest.user_id)
            .where(HelpRequest.status == HelpRequestStatus.MODERATION.value)
            .order_by(HelpRequest.created_at.asc())
            .limit(10)
        )
        items = list(rows.all())

    if not items:
        await message.answer("Заявок на модерации нет.")
        return

    for request, owner in items:
        await message.answer(admin_request_text(request, owner), reply_markup=moderation_keyboard(request.id))


@admin_router.callback_query(F.data.startswith("admin:publish:"))
async def publish_request(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionFactory() as session:
        request = await session.get(HelpRequest, request_id)
        if request is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        request.status = HelpRequestStatus.PUBLISHED.value
        await session.commit()

    await callback.message.answer(f"Заявка #{request_id} опубликована.")
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin:reject:"))
async def reject_request(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionFactory() as session:
        request = await session.get(HelpRequest, request_id)
        if request is None:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        request.status = HelpRequestStatus.REJECTED.value
        await session.commit()

    await callback.message.answer(f"Заявка #{request_id} отклонена.")
    await callback.answer()


@admin_router.message(Command("complaints"))
async def complaints_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    async with SessionFactory() as session:
        rows = await session.execute(
            select(Complaint, User)
            .join(User, User.id == Complaint.reporter_id)
            .where(Complaint.status == ComplaintStatus.NEW.value)
            .order_by(Complaint.created_at.asc())
            .limit(10)
        )
        items = list(rows.all())

    if not items:
        await message.answer("Новых жалоб нет.")
        return

    for complaint, reporter in items:
        reporter_text = f"{reporter.telegram_id}"
        if reporter.username:
            reporter_text += f" / @{reporter.username}"
        await message.answer(
            f"<b>Жалоба #{complaint.id}</b>\n"
            f"От: {reporter_text}\n"
            f"Заявка: {complaint.request_id or 'не указана'}\n\n"
            f"{complaint.reason}"
        )
