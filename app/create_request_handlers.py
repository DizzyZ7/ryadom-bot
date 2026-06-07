from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionFactory
from app.keyboards import (
    CATEGORIES,
    MAIN_MENU,
    REWARD_TYPES,
    URGENCY_TYPES,
    categories_keyboard,
    reward_keyboard,
    urgency_keyboard,
)
from app.location_keyboards import cities_keyboard, districts_keyboard
from app.models import City, District, HelpRequest, HelpRequestStatus, Offer, OfferStatus, User
from app.repositories import create_help_request, get_or_create_user
from app.states import CreateRequestState
from app.user_handlers import format_request

create_request_router = Router()

CATEGORY_LABELS = dict(CATEGORIES)
REWARD_LABELS = dict(REWARD_TYPES)
URGENCY_LABELS = dict(URGENCY_TYPES)
ACTIVE_REQUEST_STATUSES = {
    HelpRequestStatus.MODERATION.value,
    HelpRequestStatus.PUBLISHED.value,
    HelpRequestStatus.IN_PROGRESS.value,
}


async def ensure_user(message: Message, session: AsyncSession) -> User:
    return await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


async def edit_wizard_message(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    wizard_message_id = data.get("wizard_message_id")
    if wizard_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=wizard_message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramAPIError:
            pass

    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(wizard_message_id=sent.message_id)


async def edit_wizard_callback(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        await state.update_data(wizard_message_id=callback.message.message_id)
        return
    except TelegramAPIError:
        sent = await callback.message.answer(text, reply_markup=reply_markup)
        await state.update_data(wizard_message_id=sent.message_id)


@create_request_router.message(F.text == "Нужна помощь")
async def create_request_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    sent = await message.answer(
        "<b>Создание заявки</b>\n\n"
        "Шаг 1: выбери категорию.",
        reply_markup=categories_keyboard(),
    )
    await state.update_data(wizard_message_id=sent.message_id)
    await state.set_state(CreateRequestState.category)


@create_request_router.callback_query(CreateRequestState.category, F.data.startswith("category:"))
async def create_request_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    allowed_categories = {value for value, _ in CATEGORIES}
    if category not in allowed_categories:
        await callback.answer("Некорректная категория", show_alert=True)
        return

    await state.update_data(category=category)
    await state.set_state(CreateRequestState.title)
    await edit_wizard_callback(
        callback,
        state,
        "<b>Создание заявки</b>\n\n"
        f"Категория: {CATEGORY_LABELS.get(category, category)}\n\n"
        "Шаг 2: отправь короткий заголовок заявки одним сообщением.",
    )
    await callback.answer()


@create_request_router.message(CreateRequestState.title)
async def create_request_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not 5 <= len(title) <= 160:
        await edit_wizard_message(message, state, "Заголовок должен быть от 5 до 160 символов. Отправь заголовок еще раз.")
        return

    await state.update_data(title=title)
    data = await state.get_data()
    await state.set_state(CreateRequestState.description)
    await edit_wizard_message(
        message,
        state,
        "<b>Создание заявки</b>\n\n"
        f"Категория: {CATEGORY_LABELS.get(data.get('category'), data.get('category'))}\n"
        f"Заголовок: {title}\n\n"
        "Шаг 3: опиши подробнее, что нужно сделать.",
    )


@create_request_router.message(CreateRequestState.description)
async def create_request_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if len(description) < 10:
        await edit_wizard_message(message, state, "Описание слишком короткое. Отправь описание еще раз.")
        return

    await state.update_data(description=description)
    async with SessionFactory() as session:
        cities = list(await session.scalars(select(City).where(City.is_active.is_(True)).order_by(City.name.asc())))

    await state.set_state(CreateRequestState.city)
    if cities:
        await edit_wizard_message(
            message,
            state,
            "<b>Создание заявки</b>\n\n"
            "Описание сохранено.\n\n"
            "Шаг 4: выбери город заявки.",
            reply_markup=cities_keyboard(cities, "request_location"),
        )
    else:
        await edit_wizard_message(message, state, "Справочник городов пуст. Отправь город текстом.")


@create_request_router.callback_query(CreateRequestState.city, F.data.startswith("request_location:city:"))
async def create_request_city_from_catalog(callback: CallbackQuery, state: FSMContext) -> None:
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

    await state.update_data(city=city.name)
    await state.set_state(CreateRequestState.district)
    await edit_wizard_callback(
        callback,
        state,
        "<b>Создание заявки</b>\n\n"
        f"Город: {city.name}\n\n"
        "Шаг 5: выбери район заявки.",
        reply_markup=districts_keyboard(districts, "request_location"),
    )
    await callback.answer()


@create_request_router.message(CreateRequestState.city)
async def create_request_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if len(city) < 2:
        await edit_wizard_message(message, state, "Город слишком короткий. Отправь город еще раз.")
        return

    await state.update_data(city=city)
    await state.set_state(CreateRequestState.district)
    await edit_wizard_message(message, state, "Город сохранен. Отправь район или '-' если район не важен.")


@create_request_router.callback_query(CreateRequestState.district, F.data.startswith("request_location:district:"))
async def create_request_district_from_catalog(callback: CallbackQuery, state: FSMContext) -> None:
    district_id = int(callback.data.rsplit(":", 1)[1])
    district_name = None
    if district_id > 0:
        async with SessionFactory() as session:
            district = await session.get(District, district_id)
            if district is None or not district.is_active:
                await callback.answer("Район недоступен", show_alert=True)
                return
            district_name = district.name

    await state.update_data(district=district_name)
    await state.set_state(CreateRequestState.address_hint)
    await edit_wizard_callback(
        callback,
        state,
        "<b>Создание заявки</b>\n\n"
        f"Район: {district_name or 'без района'}\n\n"
        "Шаг 6: отправь ориентир или адрес без квартиры. Если не хочешь указывать, отправь '-'.",
    )
    await callback.answer()


@create_request_router.message(CreateRequestState.district)
async def create_request_district(message: Message, state: FSMContext) -> None:
    district = (message.text or "").strip()
    await state.update_data(district=None if district == "-" else district)
    await state.set_state(CreateRequestState.address_hint)
    await edit_wizard_message(message, state, "Район сохранен. Отправь ориентир или адрес без квартиры. Если не хочешь указывать, отправь '-'.")


@create_request_router.message(CreateRequestState.address_hint)
async def create_request_address(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    await state.update_data(address_hint=None if value == "-" else value)
    await state.set_state(CreateRequestState.needed_at_text)
    await edit_wizard_message(message, state, "Ориентир сохранен. Отправь, когда нужна помощь.")


@create_request_router.message(CreateRequestState.needed_at_text)
async def create_request_needed_at(message: Message, state: FSMContext) -> None:
    await state.update_data(needed_at_text=(message.text or "").strip())
    await state.set_state(CreateRequestState.urgency)
    await edit_wizard_message(
        message,
        state,
        "<b>Создание заявки</b>\n\n"
        "Время сохранено.\n\n"
        "Шаг 7: выбери срочность заявки.",
        reply_markup=urgency_keyboard(),
    )


@create_request_router.callback_query(CreateRequestState.urgency, F.data.startswith("urgency:"))
async def create_request_urgency(callback: CallbackQuery, state: FSMContext) -> None:
    urgency = callback.data.split(":", 1)[1]
    allowed_urgencies = {value for value, _ in URGENCY_TYPES}
    if urgency not in allowed_urgencies:
        await callback.answer("Некорректная срочность", show_alert=True)
        return

    await state.update_data(urgency=urgency)
    await state.set_state(CreateRequestState.reward_type)
    await edit_wizard_callback(
        callback,
        state,
        "<b>Создание заявки</b>\n\n"
        f"Срочность: {URGENCY_TYPES and dict(URGENCY_TYPES).get(urgency, urgency)}\n\n"
        "Шаг 8: выбери формат оплаты.",
        reply_markup=reward_keyboard(),
    )
    await callback.answer()


@create_request_router.callback_query(CreateRequestState.reward_type, F.data.startswith("reward:"))
async def create_request_reward(callback: CallbackQuery, state: FSMContext) -> None:
    reward_type = callback.data.split(":", 1)[1]
    allowed_rewards = {value for value, _ in REWARD_TYPES}
    if reward_type not in allowed_rewards:
        await callback.answer("Некорректный формат оплаты", show_alert=True)
        return

    await state.update_data(reward_type=reward_type)
    if reward_type == "paid":
        await state.set_state(CreateRequestState.reward_amount)
        await edit_wizard_callback(
            callback,
            state,
            "<b>Создание заявки</b>\n\n"
            "Формат оплаты: платная помощь.\n\n"
            "Шаг 9: отправь сумму числом.",
        )
    else:
        await state.update_data(reward_amount=None)
        await state.set_state(CreateRequestState.confirm)
        await edit_wizard_callback(
            callback,
            state,
            "<b>Создание заявки</b>\n\n"
            f"Формат оплаты: {REWARD_LABELS.get(reward_type, reward_type)}\n\n"
            "Финальный шаг: отправь '+' чтобы создать заявку или /cancel для отмены.",
        )
    await callback.answer()


@create_request_router.message(CreateRequestState.reward_amount)
async def create_request_reward_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await edit_wizard_message(message, state, "Сумма должна быть числом. Отправь сумму еще раз.")
        return

    if amount <= 0:
        await edit_wizard_message(message, state, "Сумма должна быть больше 0. Отправь сумму еще раз.")
        return

    await state.update_data(reward_amount=amount)
    await state.set_state(CreateRequestState.confirm)
    await edit_wizard_message(message, state, "Сумма сохранена. Отправь '+' чтобы создать заявку или /cancel для отмены.")


@create_request_router.message(CreateRequestState.confirm)
async def create_request_confirm(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() != "+":
        await edit_wizard_message(message, state, "Отправь '+' для создания заявки или /cancel для отмены.")
        return

    data = await state.get_data()
    async with SessionFactory() as session:
        user = await ensure_user(message, session)
        active_requests_count = await session.scalar(
            select(func.count())
            .select_from(HelpRequest)
            .where(HelpRequest.user_id == user.id)
            .where(HelpRequest.status.in_(ACTIVE_REQUEST_STATUSES))
        )
        if not user.is_verified and (active_requests_count or 0) >= settings.max_active_requests_per_user:
            await edit_wizard_message(
                message,
                state,
                "Лимит активных заявок достигнут. Заверши или отмени старые заявки перед созданием новой.",
            )
            await state.clear()
            return

        status = HelpRequestStatus.PUBLISHED if settings.auto_publish_without_admins else HelpRequestStatus.MODERATION
        request = await create_help_request(
            session=session,
            user=user,
            category=data["category"],
            title=data["title"],
            description=data["description"],
            city=data.get("city"),
            district=data.get("district"),
            address_hint=data.get("address_hint"),
            needed_at_text=data.get("needed_at_text"),
            urgency=data.get("urgency", "flexible"),
            reward_type=data.get("reward_type", "free"),
            reward_amount=data.get("reward_amount"),
            status=status,
        )
        text = format_request(request, owner=user)

    await edit_wizard_message(message, state, f"Заявка #{request.id} создана.")
    await state.clear()
    await message.answer(text, reply_markup=MAIN_MENU)
