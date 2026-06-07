from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionFactory
from app.keyboards import CATEGORIES, MAIN_MENU, REWARD_TYPES, URGENCY_TYPES, request_actions_keyboard
from app.models import HelpRequest, HelpRequestStatus, Offer, OfferStatus, User
from app.notifications import safe_send_message
from app.repositories import create_offer, get_or_create_user, get_request_by_id, list_published_requests, list_user_requests, update_user_location
from app.states import OfferState, ProfileState

user_router = Router()

CATEGORY_LABELS = dict(CATEGORIES)
REWARD_LABELS = dict(REWARD_TYPES)
URGENCY_LABELS = dict(URGENCY_TYPES)
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


def trust_line(user: User | None) -> str:
    if user is None:
        return "Автор: неизвестно"
    verified = "проверен" if user.is_verified else "не проверен"
    return f"Автор: {public_name(user)} | рейтинг {user.rating} ({user.rating_count} отзывов) | {verified}"


def format_request(request: HelpRequest, owner: User | None = None) -> str:
    request_owner = owner or request.__dict__.get("owner")
    location = ", ".join(item for item in [request.city, request.district] if item) or "не указано"
    reward = REWARD_LABELS.get(request.reward_type, request.reward_type)
    if request.reward_amount:
        reward = f"{reward}: {request.reward_amount}"
    urgency = URGENCY_LABELS.get(getattr(request, "urgency", "flexible"), "Не срочно")
    return (
        f"<b>#{request.id} {request.title}</b>\n"
        f"Категория: {CATEGORY_LABELS.get(request.category, request.category)}\n"
        f"Статус: {STATUS_LABELS.get(request.status, request.status)}\n"
        f"Срочность: {urgency}\n"
        f"Район: {location}\n"
        f"Когда: {request.needed_at_text or 'не указано'}\n"
        f"Оплата: {reward}\n"
        f"{trust_line(request_owner)}\n\n"
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
            f"Рейтинг: {user.rating} ({user.rating_count} отзывов)\n"
            f"Аккаунт: {'проверен' if user.is_verified else 'не проверен'}\n\n"
            "Для выбора из справочника нажми кнопку <b>Выбрать локацию</b>.\n"
            "Или отправь вручную: <code>город, район</code>"
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
        pending_offers_count = await session.scalar(
            select(func.count())
            .select_from(Offer)
            .where(Offer.helper_id == user.id)
            .where(Offer.status == OfferStatus.PENDING.value)
        )
        if not user.is_verified and (pending_offers_count or 0) >= settings.max_pending_offers_per_user:
            await message.answer(
                "Лимит ожидающих откликов достигнут. Дождись решения по старым откликам перед новым откликом."
            )
            await state.clear()
            return
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
