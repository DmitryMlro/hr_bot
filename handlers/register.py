from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from states import Registration
from database import (
    is_token_valid, mark_token_as_used,
    add_user, get_user, add_hr, has_hr_access
)
from keyboards.user_keyboards import get_user_main_menu
from keyboards.hr_keyboards import get_hr_main_menu

register_router = Router()

welcome_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Реєстрація")]],
    resize_keyboard=True
)


@register_router.message(F.text == "/start")
async def welcome(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    greeting = (
        "Привіт 👋 Вітаємо в HR-відділі. Тут ти завжди можеш надіслати звернення або поділитись анонімним фідбеком. Ми читаємо та реагуємо на кожне повідомлення 🙌"
    )
    if user:
        if has_hr_access(message.from_user.id):
            await message.answer(greeting, reply_markup=get_hr_main_menu())
        else:
            await message.answer(greeting, reply_markup=get_user_main_menu())
    else:
        await message.answer(greeting, reply_markup=welcome_kb)

    await state.clear()


@register_router.message(F.text == "Реєстрація")
async def ask_token(message: types.Message, state: FSMContext):
    await message.answer("🔐 Введіть ваш реєстраційний логін:")
    await state.set_state(Registration.token)


@register_router.message(Registration.token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    if token == "give_me_hr_t4y":
        await state.update_data(token=token)
        await message.answer("👤 Введіть ваше ПІБ:")
        await state.set_state(Registration.full_name)
        return

    if is_token_valid(token):
        mark_token_as_used(token)
        await state.update_data(token=token)
        await message.answer("👤 Введіть ваше ПІБ:")
        await state.set_state(Registration.full_name)
    else:
        await message.answer("❌ Невірний логін. Спробуйте ще раз.")


@register_router.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.answer("🏢 Вкажіть ваш відділ:")
    await state.set_state(Registration.department)


@register_router.message(Registration.department)
async def process_department(message: types.Message, state: FSMContext):
    await state.update_data(department=message.text.strip())
    await message.answer("📌 Вкажіть вашу посаду:")
    await state.set_state(Registration.position)


@register_router.message(Registration.position)
async def finish_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tg_id = message.from_user.id

    add_user(
        telegram_id=tg_id,
        full_name=data["full_name"],
        department=data["department"],
        position=message.text.strip()
    )

    if data["token"] == "give_me_hr_t4y":
        add_hr(tg_id)
        await message.answer(
            "✅ Ви успішно зареєстровані як HR!",
            reply_markup=get_hr_main_menu()
        )
    else:
        await message.answer(
            "✅ Реєстрацію завершено!",
            reply_markup=get_user_main_menu()
        )

    await state.clear()
