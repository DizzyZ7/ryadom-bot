from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.config import settings
from app.database import SessionFactory
from app.models import User
from aiogram import Router

admin_user_router = Router()


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


@admin_user_router.message(Command("user"))
async def show_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /user telegram_id")
        return

    telegram_id = int(args[1].strip())
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

    if user is None:
        await message.answer("Пользователь не найден.")
        return

    await message.answer(
        "<b>Пользователь</b>\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Username: @{user.username if user.username else '-'}\n"
        f"Имя: {user.first_name or '-'}\n"
        f"Город: {user.city or '-'}\n"
        f"Район: {user.district or '-'}\n"
        f"Рейтинг: {user.rating}\n"
        f"Забанен: {'да' if user.is_banned else 'нет'}"
    )


@admin_user_router.message(Command("ban"))
async def ban_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /ban telegram_id")
        return

    telegram_id = int(args[1].strip())
    if telegram_id == message.from_user.id:
        await message.answer("Нельзя забанить самого себя.")
        return

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.is_banned = True
        await session.commit()

    await message.answer(f"Пользователь {telegram_id} забанен.")


@admin_user_router.message(Command("unban"))
async def unban_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /unban telegram_id")
        return

    telegram_id = int(args[1].strip())
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.is_banned = False
        await session.commit()

    await message.answer(f"Пользователь {telegram_id} разбанен.")
