from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.config import settings
from app.database import SessionFactory
from app.models import Complaint, ComplaintStatus, User

admin_complaint_router = Router()


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def complaint_keyboard(complaint: Complaint) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if complaint.status == ComplaintStatus.NEW.value:
        buttons.append([InlineKeyboardButton(text="Закрыть жалобу", callback_data=f"complaint_close:{complaint.id}")])
    if complaint.target_user_id:
        buttons.append([InlineKeyboardButton(text="Забанить нарушителя", callback_data=f"complaint_ban:{complaint.id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_info(user: User | None) -> str:
    if user is None:
        return "не указан"
    result = str(user.telegram_id)
    if user.username:
        result += f" / @{user.username}"
    if user.first_name:
        result += f" / {user.first_name}"
    return result


@admin_complaint_router.message(Command("complaint"))
async def show_complaint(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /complaint complaint_id")
        return

    complaint_id = int(args[1].strip())

    async with SessionFactory() as session:
        complaint = await session.get(Complaint, complaint_id)
        if complaint is None:
            await message.answer("Жалоба не найдена.")
            return
        reporter = await session.get(User, complaint.reporter_id)
        target = await session.get(User, complaint.target_user_id) if complaint.target_user_id else None

    await message.answer(
        f"<b>Жалоба #{complaint.id}</b>\n"
        f"Статус: {complaint.status}\n"
        f"Заявка: {complaint.request_id or 'не указана'}\n"
        f"Отправитель: {user_info(reporter)}\n"
        f"Цель жалобы: {user_info(target)}\n\n"
        f"{complaint.reason}",
        reply_markup=complaint_keyboard(complaint),
    )


@admin_complaint_router.callback_query(F.data.startswith("complaint_close:"))
async def close_complaint(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    complaint_id = int(callback.data.split(":", 1)[1])
    async with SessionFactory() as session:
        complaint = await session.get(Complaint, complaint_id)
        if complaint is None:
            await callback.answer("Жалоба не найдена", show_alert=True)
            return
        complaint.status = ComplaintStatus.CLOSED.value
        await session.commit()

    await callback.message.answer(f"Жалоба #{complaint_id} закрыта.")
    await callback.answer()


@admin_complaint_router.callback_query(F.data.startswith("complaint_ban:"))
async def ban_complaint_target(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    complaint_id = int(callback.data.split(":", 1)[1])
    async with SessionFactory() as session:
        complaint = await session.get(Complaint, complaint_id)
        if complaint is None:
            await callback.answer("Жалоба не найдена", show_alert=True)
            return
        if not complaint.target_user_id:
            await callback.answer("У жалобы нет цели", show_alert=True)
            return
        target = await session.get(User, complaint.target_user_id)
        if target is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        if target.telegram_id == callback.from_user.id:
            await callback.answer("Нельзя забанить самого себя", show_alert=True)
            return
        target.is_banned = True
        complaint.status = ComplaintStatus.CLOSED.value
        await session.commit()

    await callback.message.answer(f"Пользователь {target.telegram_id} забанен. Жалоба #{complaint_id} закрыта.")
    await callback.answer()
