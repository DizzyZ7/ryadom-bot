from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.audit import write_audit_log
from app.config import settings
from app.database import SessionFactory
from app.models import User

admin_user_router = Router()


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with SessionFactory() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


def parse_telegram_id(message: Message, command_hint: str) -> int | None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        return None
    return int(args[1].strip())


@admin_user_router.message(Command("user"))
async def show_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    telegram_id = parse_telegram_id(message, "/user telegram_id")
    if telegram_id is None:
        await message.answer("Использование: /user telegram_id")
        return

    user = await get_user_by_telegram_id(telegram_id)
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
        f"Рейтинг: {user.rating} ({user.rating_count} отзывов)\n"
        f"Проверен: {'да' if user.is_verified else 'нет'}\n"
        f"Забанен: {'да' if user.is_banned else 'нет'}"
    )


@admin_user_router.message(Command("ban"))
async def ban_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    telegram_id = parse_telegram_id(message, "/ban telegram_id")
    if telegram_id is None:
        await message.answer("Использование: /ban telegram_id")
        return
    if telegram_id == message.from_user.id:
        await message.answer("Нельзя забанить самого себя.")
        return

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.is_banned = True
        await write_audit_log(
            session,
            message.from_user.id,
            action="user_ban",
            entity_type="user",
            entity_id=user.id,
            details=f"telegram_id={telegram_id}",
        )
        await session.commit()

    await message.answer(f"Пользователь {telegram_id} забанен.")


@admin_user_router.message(Command("unban"))
async def unban_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    telegram_id = parse_telegram_id(message, "/unban telegram_id")
    if telegram_id is None:
        await message.answer("Использование: /unban telegram_id")
        return

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.is_banned = False
        await write_audit_log(
            session,
            message.from_user.id,
            action="user_unban",
            entity_type="user",
            entity_id=user.id,
            details=f"telegram_id={telegram_id}",
        )
        await session.commit()

    await message.answer(f"Пользователь {telegram_id} разбанен.")


@admin_user_router.message(Command("verify"))
async def verify_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    telegram_id = parse_telegram_id(message, "/verify telegram_id")
    if telegram_id is None:
        await message.answer("Использование: /verify telegram_id")
        return

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.is_verified = True
        await write_audit_log(
            session,
            message.from_user.id,
            action="user_verify",
            entity_type="user",
            entity_id=user.id,
            details=f"telegram_id={telegram_id}",
        )
        await session.commit()

    await message.answer(f"Пользователь {telegram_id} отмечен как проверенный.")


@admin_user_router.message(Command("unverify"))
async def unverify_user(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    telegram_id = parse_telegram_id(message, "/unverify telegram_id")
    if telegram_id is None:
        await message.answer("Использование: /unverify telegram_id")
        return

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.is_verified = False
        await write_audit_log(
            session,
            message.from_user.id,
            action="user_unverify",
            entity_type="user",
            entity_id=user.id,
            details=f"telegram_id={telegram_id}",
        )
        await session.commit()

    await message.answer(f"Проверка пользователя {telegram_id} снята.")
