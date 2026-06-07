from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import MAIN_MENU
from app.states import CreateRequestState

create_cancel_router = Router()


@create_cancel_router.message(
    StateFilter(
        CreateRequestState.category,
        CreateRequestState.title,
        CreateRequestState.description,
        CreateRequestState.city,
        CreateRequestState.district,
        CreateRequestState.address_hint,
        CreateRequestState.needed_at_text,
        CreateRequestState.urgency,
        CreateRequestState.reward_type,
        CreateRequestState.reward_amount,
        CreateRequestState.confirm,
    ),
    F.text == "/cancel",
)
async def cancel_create_request(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Создание заявки отменено.", reply_markup=MAIN_MENU)
