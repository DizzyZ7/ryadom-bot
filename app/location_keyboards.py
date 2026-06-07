from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import City, District


def cities_keyboard(cities: list[City], prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=city.name, callback_data=f"{prefix}:city:{city.id}")]
        for city in cities
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def districts_keyboard(districts: list[District], prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=district.name, callback_data=f"{prefix}:district:{district.id}")]
        for district in districts
    ]
    buttons.append([InlineKeyboardButton(text="Без района", callback_data=f"{prefix}:district:0")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
