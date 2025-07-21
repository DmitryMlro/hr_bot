from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def get_hr_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Нові заявки")],
            [KeyboardButton(text="📜 Історія заявок")],
            [KeyboardButton(text="👥 Співробітники")],
            [KeyboardButton(text="⚙️ Налаштування")],
            [KeyboardButton(text="🔑 Згенерувати токен HR")],
        ],
        resize_keyboard=True
    )


def get_settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Призначити HR")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True
    )


def get_request_action_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Схвалити", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{request_id}"),
            InlineKeyboardButton(text="💬 Коментар", callback_data=f"comment_{request_id}")
        ]
    ])


def get_feedback_action_keyboard(feedback_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Відповісти", callback_data=f"reply_feedback_{feedback_id}")]
    ])


def get_user_list_keyboard(users: list) -> InlineKeyboardMarkup:
    inline_keyboard = []
    for uid, full, dept, pos in users:
        inline_keyboard.append([
            InlineKeyboardButton(text=f"✏️ {full} ({dept}, {pos})", callback_data=f"edit_user_{uid}"),
            InlineKeyboardButton(text="❌ Видалити", callback_data=f"delete_user_{uid}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_confirm_delete_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так", callback_data=f"confirm_delete_{user_id}"),
            InlineKeyboardButton(text="❌ Ні", callback_data="cancel_delete")
        ]
    ])


def get_assign_hr_keyboard(users: list) -> InlineKeyboardMarkup:
    inline_keyboard = []
    for uid, full, dept, pos in users:
        inline_keyboard.append([
            InlineKeyboardButton(text=f"{full} ({dept}, {pos})", callback_data=f"assign_hr_{uid}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
