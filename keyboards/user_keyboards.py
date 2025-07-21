from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_user_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Подати заявку")],
            [KeyboardButton(text="💬 Залишити анонімний відгук")],
            [KeyboardButton(text="📑 Перевірити статус моєї заяви")]
        ],
        resize_keyboard=True
    )


def get_category_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Відпустка / лікарняний")],
            [KeyboardButton(text="Техніка або матеріали")],
            [KeyboardButton(text="Взаємини в команді")],
            [KeyboardButton(text="Особисте звернення до HR")]
        ],
        resize_keyboard=True
    )


def get_preview_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Відправити", callback_data="send_request"),
                InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_request"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_request")
            ]
        ]
    )
