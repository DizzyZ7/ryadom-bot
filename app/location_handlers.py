from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database import SessionFactory
from app.keyboards import MAIN_MENU
from app.location_keyboards import cities_keyboard, districts_keyboard
from app.models import City, District, User
from app.states import LocationState

location_router = Router()


@location_router.message(F.text == "Выбрать локацию")
async def choose_location_start(message: Message, state: FSMContext) -> None:
    async with SessionFactory() as session:
        cities = list(await session.scalars(select(City).where(City.is_active.is_(True)).order_by(City.name.asc())))

    if not cities:
        await message.answer("Справочник городов пока пуст.")
        return

    await state.clear()
    await message.answer("Выбери город.", reply_markup=cities_keyboard(cities, "profile_location"))
    await state.set_state(LocationState.profile_city)


@location_router.callback_query(LocationState.profile_city, F.data.startswith("profile_location:city:"))
async def choose_profile_city(callback: CallbackQuery, state: FSMContext) -> None:
    city_id = int(callback.data.rsplit(":", 1)[1])

    async with SessionFactory() as session:
        city = await session.get(City, city_id)
        if city is None or not city.is_active:
            await callback.answer("Город недоступен", show_alert=True)
            return
        districts = list(
            await session.scalars(
                select(District)
                .where(District.city_id == city.id)
                .where(District.is_active.is_(True))
                .order_by(District.name.asc())
            )
        )

    await state.update_data(city_id=city.id, city_name=city.name)
    await callback.message.answer("Выбери район.", reply_markup=districts_keyboard(districts, "profile_location"))
    await state.set_state(LocationState.profile_district)
    await callback.answer()


@location_router.callback_query(LocationState.profile_district, F.data.startswith("profile_location:district:"))
async def choose_profile_district(callback: CallbackQuery, state: FSMContext) -> None:
    district_id = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    city_name = data.get("city_name")
    district_name = None

    async with SessionFactory() as session:
        if district_id > 0:
            district = await session.get(District, district_id)
            if district is None or not district.is_active:
                await callback.answer("Район недоступен", show_alert=True)
                return
            district_name = district.name

        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if user is None:
            user = User(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
            )
            session.add(user)
            await session.flush()

        user.city = city_name
        user.district = district_name
        await session.commit()

    await state.clear()
    location = ", ".join(item for item in [city_name, district_name] if item)
    await callback.message.answer(f"Локация сохранена: {location}", reply_markup=MAIN_MENU)
    await callback.answer()
