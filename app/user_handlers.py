from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionFactory
from app.keyboards import CATEGORIES, MAIN_MENU, REWARD_TYPES, categories_keyboard, request_actions_keyboard, reward_keyboard
from app.models import HelpRequest, HelpRequestStatus, User
from app.notifications import safe_send_message
from app.repositories import create_help_request, create_offer, get_or_create_user, get_request_by_id, list_published_requests, list_user_requests, update_user_location
from app.states import CreateRequestState, OfferState, ProfileState

user_router = Router()

CATEGORY_LABELS = dict(CATEGORIES)
REWARD_LABELS = dict(REWARD_TYPES)
STATUS_LABELS = {
    "moderation": "На модерации",
    "published": "Опубликована",
    "in_progress": "В работе",
    "done": "Выполнена",
    "canceled": "Отменена",
    "rejected": "Отклонена",
}


def public_name(user: User | None) -> str:
    if user is None:
        return "неизвестно"
    if user.username:
        return "@" + user.username
    return user.first_name or str(user.telegram_id)


def format_request(request: HelpRequest, owner: User | None = None) -> str:
    request_owner = owner or request.__dict__.get("owner")
    location = ", ".join(item for item in [request.city, request.district] if item) or "не указано"
    reward = REWARD_LABELS.get(request.reward_type, request.reward_type)
    if request.reward_amount:
        reward = f"{reward}: {request.reward_amount}"
    return (
        f"<b>#{request.id} {request.title}</b>\n"
        f"Категория: {CATEGORY_LABELS.get(request.category, request.category)}\n"
        f"Статус: {STATUS_LABELS.get(request.status, request.status)}\n"
        f"Район: {location}\n"
        f"Когда: {request.needed_at_text or 'не указано'}\n"
        f"Оплата: {reward}\n"
        f"Автор: {public_name(request_owner)}\n\n"
        f"{request.description}"
    )


async def ensure_user(message: Message, session: AsyncSession) -> User:
    return await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


@user_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with SessionFactory() as session:
        await ensure_user(message, session)
    await message.answer(
        "Привет. Я бот Рядом. Здесь можно попросить помощь по району или откликнуться на чужую заявку.",
        reply_markup=MAIN_MENU,
    )


@user_router.message(F.text == "/cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=MAIN_MENU)


@user_router.message(F.text == "Правила безопасности")
async def safety_handler(message: Message) -> None:
    await message.answer(
        "<b>Правила безопасности</b>\n\n"
        "1. Не отправляй предоплату незнакомым людям.\n"
        "2. Не передавай паспортные данные и коды из SMS.\n"
        "3. Для встреч выбирай публичные места.\n"
        "4. Проверяй чеки и договоренности в переписке.\n"
        "5. Если заявка подозрительная, лучше не продолжать общение."
    )


@user_router.message(F.text == "Профиль")
async def profile_handler(message: Message, state: FSMContext) -> None:
    async with SessionFactory() as session:
        user = await ensure_user(message, session)
        location = ", ".join(item for item in [user.city, user.district] if item) or "не указано"
        await message.answer(
            "<b>Профиль</b>\n"
            f"Локация: {location}\n"
            f"Рейтинг: {user.rating} ({user.rating_count} отзывов)\n\n"
            "Чтобы изменить город и район, отправь: <code>город, район</code>"
        )
    await state.set_state(ProfileState.city)


@user_router.message(ProfileState.city)
async def save_profile_location(message: Message, state: FSMContext) -> None:
    city, _, district = (message.text or "").partition(",")
    city = city.strip()
    district = district.strip() or None
    if len(city) < 2:
        await message.answer("Отправь так: Алматы, Бостандыкский")
        return
    async with SessionFactory() as session:
        user = await ensure_user(message, session)
        await update_user_location(session, user, city, district)
    await state.clear()
    await message.answer("Локация сохранена.", reply_markup=MAIN_MENU)


@user_router.message(F.text == "Нужна помощь")
async def create_request_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Выбери категорию заявки.", reply_markup=categories_keyboard())
    await state.set_state(CreateRequestState.category)


@user_router.callback_query(CreateRequestState.category, F.data.startswith("category:"))
async def create_request_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(category=callback.data.split(":", 1)[1])
    await callback.message.answer("Короткий заголовок заявки.")
    await state.set_state(CreateRequestState.title)
    await callback.answer()


@user_router.message(CreateRequestState.title)
async def create_request_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not 5 <= len(title) <= 160:
        await message.answer("Заголовок должен быть от 5 до 160 символов.")
        return
    await state.update_data(title=title)
    await message.answer("Опиши подробнее, что нужно сделать.")
    await state.set_state(CreateRequestState.description)


@user_router.message(CreateRequestState.description)
async def create_request_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if len(description) < 10:
        await message.answer("Описание слишком короткое.")
        return
    await state.update_data(description=description)
    await message.answer("Укажи город.")
    await state.set_state(CreateRequestState.city)


@user_router.message(CreateRequestState.city)
async def create_request_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if len(city) < 2:
        await message.answer("Город слишком короткий.")
        return
    await state.update_data(city=city)
    await message.answer("Укажи район. Если не важно, напиши -")
    await state.set_state(CreateRequestState.district)


@user_router.message(CreateRequestState.district)
async def create_request_district(message: Message, state: FSMContext) -> None:
    district = (message.text or "").strip()
    await state.update_data(district=None if district == "-" else district)
    await message.answer("Ориентир или адрес без квартиры. Если не хочешь указывать, напиши -")
    await state.set_state(CreateRequestState.address_hint)


@user_router.message(CreateRequestState.address_hint)
async def create_request_address(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    await state.update_data(address_hint=None if value == "-" else value)
    await message.answer("Когда нужна помощь?")
    await state.set_state(CreateRequestState.needed_at_text)


@user_router.message(CreateRequestState.needed_at_text)
async def create_request_needed_at(message: Message, state: FSMContext) -> None:
    await state.update_data(needed_at_text=(message.text or "").strip())
    await message.answer("Выбери формат оплаты.", reply_markup=reward_keyboard())
    await state.set_state(CreateRequestState.reward_type)


@user_router.callback_query(CreateRequestState.reward_type, F.data.startswith("reward:"))
async def create_request_reward(callback: CallbackQuery, state: FSMContext) -> None:
    reward_type = callback.data.split(":", 1)[1]
    await state.update_data(reward_type=reward_type)
    if reward_type == "paid":
        await callback.message.answer("Укажи сумму числом.")
        await state.set_state(CreateRequestState.reward_amount)
    else:
        await state.update_data(reward_amount=None)
        await callback.message.answer("Отправь + чтобы создать заявку.")
        await state.set_state(CreateRequestState.confirm)
    await callback.answer()


@user_router.message(CreateRequestState.reward_amount)
async def create_request_reward_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше 0.")
        return
    await state.update_data(reward_amount=amount)
    await message.answer("Отправь + чтобы создать заявку.")
    await state.set_state(CreateRequestState.confirm)


@user_router.message(CreateRequestState.confirm)
async def create_request_confirm(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() != "+":
        await message.answer("Отправь + для создания заявки или /cancel для отмены.")
        return
    data = await state.get_data()
    async with SessionFactory() as session:
        user = await ensure_user(message, session)
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
            reward_type=data.get("reward_type", "free"),
            reward_amount=data.get("reward_amount"),
            status=status,
        )
        text = format_request(request, owner=user)
    await state.clear()
    await message.answer("Заявка создана.", reply_markup=MAIN_MENU)
    await message.answer(text)


@user_router.message(F.text.in_({"Заявки рядом", "Хочу помочь"}))
async def nearby_requests_handler(message: Message) -> None:
    async with SessionFactory() as session:
        user = await ensure_user(message, session)
        requests = await list_published_requests(session, user.city, user.district, limit=10)
        if not requests:
            requests = await list_published_requests(session, user.city, None, limit=10)
        prepared = [(request, format_request(request), request.__dict__.get("owner")) for request in requests]
    if not prepared:
        await message.answer("Пока нет опубликованных заявок рядом.")
        return
    for request, text, owner in prepared:
        owner_id = owner.telegram_id if owner else 0
        await message.answer(text, reply_markup=request_actions_keyboard(request.id, owner_id, message.from_user.id))


@user_router.message(F.text == "Мои заявки")
async def my_requests_handler(message: Message) -> None:
    async with SessionFactory() as session:
        user = await ensure_user(message, session)
        requests = await list_user_requests(session, user, limit=10)
        prepared = [format_request(request, owner=user) + f"\n\nУправление: /request {request.id}" for request in requests]
    if not prepared:
        await message.answer("У тебя пока нет заявок.")
        return
    for text in prepared:
        await message.answer(text)


@user_router.callback_query(F.data.startswith("offer:"))
async def offer_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(request_id=int(callback.data.split(":", 1)[1]))
    await callback.message.answer("Напиши коротко, чем можешь помочь.")
    await state.set_state(OfferState.message)
    await callback.answer()


@user_router.message(OfferState.message)
async def offer_save(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    offer_message = (message.text or "").strip()
    if len(offer_message) < 3:
        await message.answer("Слишком коротко.")
        return

    owner_telegram_id: int | None = None
    request_id: int | None = None
    helper_label = "пользователь"

    async with SessionFactory() as session:
        user = await ensure_user(message, session)
        request = await get_request_by_id(session, int(data["request_id"]))
        if request is None or request.status != HelpRequestStatus.PUBLISHED.value:
            await message.answer("Заявка уже недоступна.")
            await state.clear()
            return
        if request.user_id == user.id:
            await message.answer("Нельзя откликнуться на свою заявку.")
            await state.clear()
            return
        await create_offer(session, request, user, offer_message)
        owner = request.__dict__.get("owner")
        owner_telegram_id = owner.telegram_id if owner else None
        request_id = request.id
        helper_label = public_name(user)

    await state.clear()
    await message.answer("Отклик сохранен. Автор заявки увидит его в разделе откликов.", reply_markup=MAIN_MENU)

    if owner_telegram_id and request_id:
        await safe_send_message(
            message.bot,
            owner_telegram_id,
            f"Новый отклик по заявке #{request_id}\n"
            f"От: {helper_label}\n\n"
            f"{offer_message}\n\n"
            "Открой: /offers",
        )
