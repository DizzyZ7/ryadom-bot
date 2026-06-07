from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Нужна помощь"), KeyboardButton(text="Хочу помочь")],
        [KeyboardButton(text="Заявки рядом"), KeyboardButton(text="Мои заявки")],
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Правила безопасности")],
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
