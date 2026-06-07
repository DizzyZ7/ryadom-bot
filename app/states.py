from aiogram.fsm.state import State, StatesGroup


class CreateRequestState(StatesGroup):
    category = State()
    title = State()
    description = State()
    city = State()
    district = State()
    address_hint = State()
    needed_at_text = State()
    urgency = State()
    reward_type = State()
    reward_amount = State()
    confirm = State()


class ProfileState(StatesGroup):
    city = State()
    district = State()


class LocationState(StatesGroup):
    profile_city = State()
    profile_district = State()


class RequestFilterState(StatesGroup):
    category = State()
    urgency = State()
    scope = State()


class OfferState(StatesGroup):
    message = State()


class ComplaintState(StatesGroup):
    reason = State()
