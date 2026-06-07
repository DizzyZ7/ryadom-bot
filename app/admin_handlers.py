from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from app.audit import write_audit_log
from app.config import settings
from app.database import SessionFactory
from app.keyboards import URGENCY_TYPES
from app.models import Complaint, ComplaintStatus, HelpRequest, HelpRequestStatus, User

admin_router = Router()
URGENCY_LABELS = dict(URGENCY_TYPES)
PAGE_SIZE = 1

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


def admin_request_text(request: HelpRequest, owner: User | None, page: int | None = None, total: int | None = None) -> str:
    owner_text = "неизвестно"
    if owner:
        owner_text = f"{owner.telegram_id}"
        if owner.username:
            owner_text += f" / @{owner.username}"
    location = ", ".join(item for item in [request.city, request.district] if item) or "не указано"
    urgency = URGENCY_LABELS.get(getattr(request, "urgency", "flexible"), "Не срочно")
    page_text = f"Страница: {page}/{total}\n" if page and total else ""
    return (
        f"<b>Заявка на модерации</b>\n"
        f"{page_text}"
        f"ID: #{request.id}\n"
        f"Статус: {STATUS_LABELS.get(request.status, request.status)}\n"
        f"Срочность: {urgency}\n"
        f"Автор: {owner_text}\n"
        f"Категория: {request.category}\n"
        f"Локация: {location}\n"
        f"Когда: {request.needed_at_text or 'не указано'}\n\n"
        f"<b>{request.title}</b>\n"
        f"{request.description}"
    )


def complaint_text(complaint: Complaint, reporter: User | None, page: int, total: int) -> str:
    reporter_text = "неизвестно"
    if reporter:
        reporter_text = str(reporter.telegram_id)
        if reporter.username:
            reporter_text += f" / @{reporter.username}"
    return (
        f"<b>Жалоба</b>\n"
        f"Страница: {page}/{total}\n"
        f"ID: #{complaint.id}\n"
        f"От: {reporter_text}\n"
        f"Заявка: {complaint.request_id or 'не указана'}\n\n"
        f"{complaint.reason}\n\n"
        f"Действия: /complaint {complaint.id}"
    )


def moderation_keyboard(request_id: int, offset: int, total: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="Опубликовать", callback_data=f"admin:publish:{request_id}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"admin:reject:{request_id}"),
        ]
    ]
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"admin:moderation:{offset - 1}"))
    if offset + 1 < total:
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"admin:moderation:{offset + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def complaints_keyboard(offset: int, total: int) -> InlineKeyboardMarkup:
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"admin:complaints:{offset - 1}"))
    if offset + 1 < total:
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"admin:complaints:{offset + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[nav] if nav else [])


async def get_moderation_page(offset: int) -> tuple[HelpRequest | None, User | None, int, int]:
    offset = max(offset, 0)
    async with SessionFactory() as session:
        total = await session.scalar(
            select(func.count()).select_from(HelpRequest).where(HelpRequest.status == HelpRequestStatus.MODERATION.value)
        )
        total = total or 0
        if total <= 0:
            return None, None, 0, 0
        if offset >= total:
            offset = total - 1
        row = await session.execute(
            select(HelpRequest, User)
            .join(User, User.id == HelpRequest.user_id)
            .where(HelpRequest.status == HelpRequestStatus.MODERATION.value)
            .order_by(HelpRequest.created_at.asc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        item = row.one_or_none()
    if item is None:
        return None, None, offset, total
    request, owner = item
    return request, owner, offset, total


async def get_complaint_page(offset: int) -> tuple[Complaint | None, User | None, int, int]:
    offset = max(offset, 0)
    async with SessionFactory() as session:
        total = await session.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.status == ComplaintStatus.NEW.value)
        )
        total = total or 0
        if total <= 0:
            return None, None, 0, 0
        if offset >= total:
            offset = total - 1
        row = await session.execute(
            select(Complaint, User)
            .join(User, User.id == Complaint.reporter_id)
            .where(Complaint.status == ComplaintStatus.NEW.value)
            .order_by(Complaint.created_at.asc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        item = row.one_or_none()
    if item is None:
        return None, None, offset, total
    complaint, reporter = item
    return complaint, reporter, offset, total


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
        "/complaints — новые жалобы\n"
        "/audit — журнал действий"
    )


@admin_router.message(Command("moderation"))
async def moderation_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    request, owner, offset, total = await get_moderation_page(0)
    if request is None:
        await message.answer("Заявок на модерации нет.")
        return

    await message.answer(
        admin_request_text(request, owner, offset + 1, total),
        reply_markup=moderation_keyboard(request.id, offset, total),
    )


@admin_router.callback_query(F.data.startswith("admin:moderation:"))
async def moderation_page(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    offset = int(callback.data.rsplit(":", 1)[1])
    request, owner, offset, total = await get_moderation_page(offset)
    if request is None:
        await callback.message.edit_text("Заявок на модерации нет.")
        await callback.answer()
        return

    await callback.message.edit_text(
        admin_request_text(request, owner, offset + 1, total),
        reply_markup=moderation_keyboard(request.id, offset, total),
    )
    await callback.answer()


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
        await write_audit_log(
            session,
            callback.from_user.id,
            action="request_publish",
            entity_type="help_request",
            entity_id=request_id,
        )
        await session.commit()

    await callback.message.edit_text(f"Заявка #{request_id} опубликована.")
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
        await write_audit_log(
            session,
            callback.from_user.id,
            action="request_reject",
            entity_type="help_request",
            entity_id=request_id,
        )
        await session.commit()

    await callback.message.edit_text(f"Заявка #{request_id} отклонена.")
    await callback.answer()


@admin_router.message(Command("complaints"))
async def complaints_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    complaint, reporter, offset, total = await get_complaint_page(0)
    if complaint is None:
        await message.answer("Новых жалоб нет.")
        return

    await message.answer(
        complaint_text(complaint, reporter, offset + 1, total),
        reply_markup=complaints_keyboard(offset, total),
    )


@admin_router.callback_query(F.data.startswith("admin:complaints:"))
async def complaints_page(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    offset = int(callback.data.rsplit(":", 1)[1])
    complaint, reporter, offset, total = await get_complaint_page(offset)
    if complaint is None:
        await callback.message.edit_text("Новых жалоб нет.")
        await callback.answer()
        return

    await callback.message.edit_text(
        complaint_text(complaint, reporter, offset + 1, total),
        reply_markup=complaints_keyboard(offset, total),
    )
    await callback.answer()
