from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from app.config import settings
from app.database import SessionFactory
from app.models import ModerationLog, User

admin_audit_router = Router()
PAGE_SIZE = 5


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def moderator_label(user: User | None) -> str:
    if user is None:
        return "unknown"
    if user.username:
        return "@" + user.username
    return str(user.telegram_id)


def audit_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"admin:audit:{page - 1}"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"admin:audit:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[nav] if nav else [])


def render_audit_page(items: list[tuple[ModerationLog, User | None]], page: int, total_pages: int, total: int) -> str:
    parts = [f"<b>Журнал действий</b>\nСтраница: {page + 1}/{total_pages}\nВсего записей: {total}"]
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
    return "\n".join(parts)


async def get_audit_page(page: int) -> tuple[list[tuple[ModerationLog, User | None]], int, int, int]:
    page = max(page, 0)
    async with SessionFactory() as session:
        total = await session.scalar(select(func.count()).select_from(ModerationLog))
        total = total or 0
        if total <= 0:
            return [], 0, 0, 0
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        if page >= total_pages:
            page = total_pages - 1
        rows = await session.execute(
            select(ModerationLog, User)
            .outerjoin(User, User.id == ModerationLog.moderator_id)
            .order_by(ModerationLog.created_at.desc())
            .offset(page * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
        items = list(rows.all())
    return items, page, total_pages, total


@admin_audit_router.message(Command("audit"))
async def audit_log(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    items, page, total_pages, total = await get_audit_page(0)
    if not items:
        await message.answer("Журнал аудита пуст.")
        return

    await message.answer(
        render_audit_page(items, page, total_pages, total),
        reply_markup=audit_keyboard(page, total_pages),
    )


@admin_audit_router.callback_query(F.data.startswith("admin:audit:"))
async def audit_page(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    page = int(callback.data.rsplit(":", 1)[1])
    items, page, total_pages, total = await get_audit_page(page)
    if not items:
        await callback.message.edit_text("Журнал аудита пуст.")
        await callback.answer()
        return

    await callback.message.edit_text(
        render_audit_page(items, page, total_pages, total),
        reply_markup=audit_keyboard(page, total_pages),
    )
    await callback.answer()
