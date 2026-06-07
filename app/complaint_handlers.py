from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database import SessionFactory
from app.models import Complaint
from app.repositories import get_or_create_user, get_request_by_id
from app.states import ComplaintState

complaint_router = Router()


@complaint_router.callback_query(F.data.startswith("complain:"))
async def complaint_start(callback: CallbackQuery, state: FSMContext) -> None:
    request_id = int(callback.data.split(":", 1)[1])
    await state.update_data(request_id=request_id)
    await callback.message.answer("Опиши, что не так с этой заявкой или пользователем.")
    await state.set_state(ComplaintState.reason)
    await callback.answer()


@complaint_router.message(ComplaintState.reason)
async def complaint_save(message: Message, state: FSMContext) -> None:
    reason = (message.text or "").strip()
    if len(reason) < 5:
        await message.answer("Жалоба слишком короткая. Напиши хотя бы 5 символов.")
        return

    data = await state.get_data()
    request_id = int(data["request_id"])

    async with SessionFactory() as session:
        reporter = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        request = await get_request_by_id(session, request_id)
        target_user_id = request.user_id if request else None
        complaint = Complaint(
            request_id=request_id if request else None,
            reporter_id=reporter.id,
            target_user_id=target_user_id,
            reason=reason,
        )
        session.add(complaint)
        await session.commit()

    await state.clear()
    await message.answer("Жалоба отправлена модераторам.")
