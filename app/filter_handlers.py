from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database import SessionFactory
from app.keyboards import (
    CATEGORIES,
    MAIN_MENU,
    URGENCY_TYPES,
    filter_category_keyboard,
    filter_scope_keyboard,
    filter_urgency_keyboard,
    request_actions_keyboard,
)
from app.repositories import get_or_create_user, list_filtered_requests
from app.states import RequestFilterState
from app.user_handlers import format_request

filter_router = Router()

CATEGORY_LABELS = dict(CATEGORIES)
URGENCY_LABELS = dict(URGENCY_TYPES)
SCOPE_LABELS = {
    "district": "мой район",
    "city": "весь город",
    "all": "все города",
}


@filter_router.message(F.text == "Фильтр заявок")
async def filter_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RequestFilterState.category)
    await message.answer(
        "<b>Фильтр заявок</b>\n\n"
        "Шаг 1 из 3: выбери категорию.",
        reply_markup=filter_category_keyboard(),
    )


@filter_router.callback_query(RequestFilterState.category, F.data.startswith("filter_category:"))
async def filter_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    allowed_categories = {value for value, _ in CATEGORIES}
    if category != "any" and category not in allowed_categories:
        await callback.answer("Некорректная категория", show_alert=True)
        return

    await state.update_data(category=None if category == "any" else category)
    await state.set_state(RequestFilterState.urgency)

    category_label = CATEGORY_LABELS.get(category, "любая категория") if category != "any" else "любая категория"
    await callback.message.edit_text(
        "<b>Фильтр заявок</b>\n\n"
        f"Категория: {category_label}\n\n"
        "Шаг 2 из 3: выбери срочность.",
        reply_markup=filter_urgency_keyboard(),
    )
    await callback.answer()


@filter_router.callback_query(RequestFilterState.urgency, F.data.startswith("filter_urgency:"))
async def filter_urgency(callback: CallbackQuery, state: FSMContext) -> None:
    urgency = callback.data.split(":", 1)[1]
    allowed_urgencies = {value for value, _ in URGENCY_TYPES}
    if urgency != "any" and urgency not in allowed_urgencies:
        await callback.answer("Некорректная срочность", show_alert=True)
        return

    await state.update_data(urgency=None if urgency == "any" else urgency)
    await state.set_state(RequestFilterState.scope)

    data = await state.get_data()
    category = data.get("category")
    category_label = CATEGORY_LABELS.get(category, "любая категория") if category else "любая категория"
    urgency_label = URGENCY_LABELS.get(urgency, "любая срочность") if urgency != "any" else "любая срочность"

    await callback.message.edit_text(
        "<b>Фильтр заявок</b>\n\n"
        f"Категория: {category_label}\n"
        f"Срочность: {urgency_label}\n\n"
        "Шаг 3 из 3: выбери зону поиска.",
        reply_markup=filter_scope_keyboard(),
    )
    await callback.answer()


@filter_router.callback_query(RequestFilterState.scope, F.data.startswith("filter_scope:"))
async def filter_scope(callback: CallbackQuery, state: FSMContext) -> None:
    scope = callback.data.split(":", 1)[1]
    if scope not in SCOPE_LABELS:
        await callback.answer("Некорректная зона поиска", show_alert=True)
        return

    data = await state.get_data()
    category = data.get("category")
    urgency = data.get("urgency")

    async with SessionFactory() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
        city = user.city if scope in {"district", "city"} else None
        district = user.district if scope == "district" else None
        requests = await list_filtered_requests(
            session=session,
            city=city,
            district=district,
            category=category,
            urgency=urgency,
            limit=10,
        )
        prepared = [(request, format_request(request), request.__dict__.get("owner")) for request in requests]

    await state.clear()

    category_label = CATEGORY_LABELS.get(category, "любая категория") if category else "любая категория"
    urgency_label = URGENCY_LABELS.get(urgency, "любая срочность") if urgency else "любая срочность"
    scope_label = SCOPE_LABELS[scope]

    await callback.message.edit_text(
        "<b>Фильтр заявок</b>\n\n"
        f"Категория: {category_label}\n"
        f"Срочность: {urgency_label}\n"
        f"Зона: {scope_label}\n\n"
        f"Найдено: {len(prepared)}",
    )

    if not prepared:
        await callback.answer("Ничего не найдено")
        return

    for request, text, owner in prepared:
        owner_id = owner.telegram_id if owner else 0
        await callback.message.answer(
            text,
            reply_markup=request_actions_keyboard(request.id, owner_id, callback.from_user.id),
        )

    await callback.answer()
