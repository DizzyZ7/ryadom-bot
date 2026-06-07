from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from app.audit import write_audit_log
from app.config import settings
from app.database import SessionFactory
from app.models import City, District

admin_location_router = Router()
PAGE_SIZE = 1


def is_admin(telegram_id: int) -> bool:
    return settings.is_admin(telegram_id)


def location_keyboard(offset: int, total: int) -> InlineKeyboardMarkup | None:
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="Назад", callback_data=f"admin:locations:{offset - 1}"))
    if offset + 1 < total:
        nav.append(InlineKeyboardButton(text="Далее", callback_data=f"admin:locations:{offset + 1}"))
    if not nav:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[nav])


def render_location_page(city: City, districts: list[District], offset: int, total: int) -> str:
    city_status = "активен" if city.is_active else "скрыт"
    parts = [
        "<b>Справочник локаций</b>",
        f"Страница: {offset + 1}/{total}",
        f"Город: {city.id}. {city.name} — {city_status}",
        "",
        "<b>Районы</b>",
    ]
    if districts:
        for district in districts:
            district_status = "активен" if district.is_active else "скрыт"
            parts.append(f"- {district.id}. {district.name} — {district_status}")
    else:
        parts.append("- районов нет")
    parts.extend(
        [
            "",
            "Команды:",
            "/addcity Название города",
            f"/adddistrict {city.id} Название района",
            f"/hidecity {city.id}",
            "/hidedistrict district_id",
        ]
    )
    return "\n".join(parts)


async def get_location_page(offset: int) -> tuple[City | None, list[District], int, int]:
    offset = max(offset, 0)
    async with SessionFactory() as session:
        total = await session.scalar(select(func.count()).select_from(City))
        total = total or 0
        if total <= 0:
            return None, [], 0, 0
        if offset >= total:
            offset = total - 1
        city = await session.scalar(select(City).order_by(City.name.asc()).offset(offset).limit(PAGE_SIZE))
        if city is None:
            return None, [], offset, total
        districts = list(
            await session.scalars(
                select(District)
                .where(District.city_id == city.id)
                .order_by(District.name.asc())
            )
        )
    return city, districts, offset, total


@admin_location_router.message(Command("locations"))
async def locations_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    city, districts, offset, total = await get_location_page(0)
    if city is None:
        await message.answer("Справочник локаций пуст.")
        return

    await message.answer(
        render_location_page(city, districts, offset, total),
        reply_markup=location_keyboard(offset, total),
    )


@admin_location_router.callback_query(F.data.startswith("admin:locations:"))
async def locations_page(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    offset = int(callback.data.rsplit(":", 1)[1])
    city, districts, offset, total = await get_location_page(offset)
    if city is None:
        await callback.message.edit_text("Справочник локаций пуст.")
        await callback.answer()
        return

    await callback.message.edit_text(
        render_location_page(city, districts, offset, total),
        reply_markup=location_keyboard(offset, total),
    )
    await callback.answer()


@admin_location_router.message(Command("addcity"))
async def add_city(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or len(args[1].strip()) < 2:
        await message.answer("Использование: /addcity Название города")
        return

    city_name = args[1].strip()
    async with SessionFactory() as session:
        existing = await session.scalar(select(City).where(City.name == city_name))
        if existing:
            existing.is_active = True
            city_id = existing.id
            action = "city_reactivate"
        else:
            city = City(name=city_name, is_active=True)
            session.add(city)
            await session.flush()
            city_id = city.id
            action = "city_create"
        await write_audit_log(
            session,
            message.from_user.id,
            action=action,
            entity_type="city",
            entity_id=city_id,
            details=city_name,
        )
        await session.commit()

    await message.answer(f"Город сохранен: {city_name}")


@admin_location_router.message(Command("adddistrict"))
async def add_district(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=2)
    if len(args) < 3 or not args[1].isdigit() or len(args[2].strip()) < 2:
        await message.answer("Использование: /adddistrict city_id Название района")
        return

    city_id = int(args[1])
    district_name = args[2].strip()
    async with SessionFactory() as session:
        city = await session.get(City, city_id)
        if city is None:
            await message.answer("Город не найден.")
            return
        existing = await session.scalar(
            select(District).where(District.city_id == city_id).where(District.name == district_name)
        )
        if existing:
            existing.is_active = True
            district_id = existing.id
            action = "district_reactivate"
        else:
            district = District(city_id=city_id, name=district_name, is_active=True)
            session.add(district)
            await session.flush()
            district_id = district.id
            action = "district_create"
        await write_audit_log(
            session,
            message.from_user.id,
            action=action,
            entity_type="district",
            entity_id=district_id,
            details=f"city_id={city_id}; name={district_name}",
        )
        await session.commit()

    await message.answer(f"Район сохранен: {district_name}")


@admin_location_router.message(Command("hidecity"))
async def hide_city(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /hidecity city_id")
        return

    city_id = int(args[1].strip())
    async with SessionFactory() as session:
        city = await session.get(City, city_id)
        if city is None:
            await message.answer("Город не найден.")
            return
        city.is_active = False
        await write_audit_log(
            session,
            message.from_user.id,
            action="city_hide",
            entity_type="city",
            entity_id=city_id,
            details=city.name,
        )
        await session.commit()

    await message.answer(f"Город скрыт: {city.name}")


@admin_location_router.message(Command("hidedistrict"))
async def hide_district(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /hidedistrict district_id")
        return

    district_id = int(args[1].strip())
    async with SessionFactory() as session:
        district = await session.get(District, district_id)
        if district is None:
            await message.answer("Район не найден.")
            return
        district.is_active = False
        await write_audit_log(
            session,
            message.from_user.id,
            action="district_hide",
            entity_type="district",
            entity_id=district_id,
            details=district.name,
        )
        await session.commit()

    await message.answer(f"Район скрыт: {district.name}")
