from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Нужна помощь"), KeyboardButton(text="Хочу помочь")],
        [KeyboardButton(text="Заявки рядом"), KeyboardButton(text="Фильтр заявок")],
        [KeyboardButton(text="Мои заявки"), KeyboardButton(text="Мои отклики")],
        [KeyboardButton(text="Отклики по моим заявкам"), KeyboardButton(text="Мой профиль")],
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Выбрать локацию")],
        [KeyboardButton(text="Правила безопасности")],
    ],
    resize_keyboard=True,
)

CATEGORIES = [
    ("delivery", "Купить / привезти"),
    ("physical", "Помочь физически"),
    ("giveaway", "Отдать вещь"),
    ("lost_found", "Найти вещь"),
    ("pets", "Питомцы"),
    ("elderly", "Пожилые люди"),
    ("family", "Дети / семья"),
    ("documents", "Документы / сопровождение"),
    ("urgent_home", "Экстренное бытовое"),
    ("other", "Другое"),
]

REWARD_TYPES = [
    ("free", "Бесплатно"),
    ("receipt", "Компенсация по чеку"),
    ("paid", "Платная помощь"),
]

URGENCY_TYPES = [
    ("urgent", "Срочно"),
    ("today", "Сегодня"),
    ("tomorrow", "Завтра"),
    ("week", "На неделе"),
    ("flexible", "Не срочно"),
]


def categories_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"category:{value}")]
        for value, label in CATEGORIES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def reward_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"reward:{value}")]
        for value, label in REWARD_TYPES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def urgency_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"urgency:{value}")]
        for value, label in URGENCY_TYPES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_request_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Создать заявку", callback_data="create_request:confirm"),
                InlineKeyboardButton(text="Отменить", callback_data="create_request:cancel"),
            ]
        ]
    )


def filter_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="Любая категория", callback_data="filter_category:any")]]
    buttons.extend(
        [InlineKeyboardButton(text=label, callback_data=f"filter_category:{value}")]
        for value, label in CATEGORIES
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def filter_urgency_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="Любая срочность", callback_data="filter_urgency:any")]]
    buttons.extend(
        [InlineKeyboardButton(text=label, callback_data=f"filter_urgency:{value}")]
        for value, label in URGENCY_TYPES
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def filter_scope_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мой район", callback_data="filter_scope:district")],
            [InlineKeyboardButton(text="Весь город", callback_data="filter_scope:city")],
            [InlineKeyboardButton(text="Все города", callback_data="filter_scope:all")],
        ]
    )


def request_actions_keyboard(request_id: int, owner_telegram_id: int, current_telegram_id: int) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if owner_telegram_id != current_telegram_id:
        buttons.append([InlineKeyboardButton(text="Откликнуться", callback_data=f"offer:{request_id}")])
    buttons.append([InlineKeyboardButton(text="Пожаловаться", callback_data=f"complain:{request_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def moderation_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Опубликовать", callback_data=f"mod_publish:{request_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"mod_reject:{request_id}"),
            ]
        ]
    )
