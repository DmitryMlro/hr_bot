from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from datetime import datetime
from states import Registration, RequestState, FeedbackState
from keyboards.user_keyboards import (
    get_user_main_menu,
    get_category_keyboard,
    get_preview_keyboard
)
from database import (
    is_token_valid,
    mark_token_as_used,
    get_user,
    add_user,
    add_request,
    get_request,
    get_user_requests,
    get_user_feedback,
    get_all_hr_ids,
    add_anonymous_feedback,
    get_new_feedback
)

import uuid

user_router = Router()
PAGE_SIZE = 10


@user_router.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    if get_user(message.from_user.id):
        await message.answer(
            "Привіт 👋 Вітаємо в HR-відділі. Тут ти завжди можеш надіслати звернення або поділитись анонімним фідбеком. Ми читаємо та реагуємо на кожне повідомлення 🙌",
            reply_markup=get_user_main_menu()
        )
    else:
        await message.answer("🔐 Введіть реєстраційний логін:")
        await state.set_state(Registration.token)


@user_router.message(Registration.token)
async def token_handler(message: Message, state: FSMContext):
    token = message.text.strip()
    if is_token_valid(token):
        await state.update_data(token=token)
        await message.answer("👤 Введіть ПІБ:")
        await state.set_state(Registration.full_name)
    else:
        await message.answer("🚫 Невірний логін. Спробуйте ще раз.")


@user_router.message(Registration.full_name)
async def full_name_handler(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.answer("🏢 Вкажіть відділ:")
    await state.set_state(Registration.department)


@user_router.message(Registration.department)
async def department_handler(message: Message, state: FSMContext):
    await state.update_data(department=message.text.strip())
    await message.answer("💼 Вкажіть посаду:")
    await state.set_state(Registration.position)


@user_router.message(Registration.position)
async def position_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    add_user(
        message.from_user.id,
        data["full_name"],
        data["department"],
        message.text.strip()
    )
    mark_token_as_used(data["token"])
    await message.answer(
        "✅ Реєстрацію завершено!",
        reply_markup=get_user_main_menu()
    )
    await state.clear()


@user_router.message(F.text == "📩 Подати заявку")
async def new_request(message: Message, state: FSMContext):
    await message.answer(
        "Чудово! Обери тему, а ми вже підключаємось до вирішення твого запитання👇",
        reply_markup=get_category_keyboard()
    )
    await state.set_state(RequestState.choose_category)


@user_router.message(RequestState.choose_category)
async def category_chosen(message: Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await message.answer("📝 Опиши суть запиту — не бійся деталей. Що сталось? Як ми можемо допомогти?")
    await state.set_state(RequestState.enter_text)


@user_router.message(RequestState.enter_text)
async def text_or_media_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("media", [])
    text = data.get("text", "")

    if message.text:
        text = message.text.strip()
    elif message.caption:
        text = message.caption.strip()

    if message.photo:
        media_list.append(("photo", message.photo[-1].file_id))
    if message.document:
        media_list.append(("document", message.document.file_id))
    if message.video:
        media_list.append(("video", message.video.file_id))
    if message.voice:
        media_list.append(("voice", message.voice.file_id))

    await state.update_data(text=text, media=media_list)

    preview_text = (
        f"📄 <b>Перевірте заявку:</b>\n\n"
        f"📂 {data['category']}\n"
        f"📝 {text or '-'}"
    )
    if media_list:
        preview_text += f"\n\n📎 Додано файлів: {len(media_list)}"

    await message.answer(preview_text, parse_mode="HTML", reply_markup=get_preview_keyboard())
    await state.set_state(RequestState.confirm)


@user_router.callback_query(F.data == "send_request")
async def confirm_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data.get("text") or ""
    rid = add_request(callback.from_user.id, data["category"], text)
    _, num = get_request(rid)

    rec = get_user(callback.from_user.id)
    full_name, department, position = rec[1], rec[2], rec[3]
    username = callback.from_user.username or "—"

    for hr_id in get_all_hr_ids():
        await callback.bot.send_message(
            hr_id,
            (
                f"🆕 <b>Нова заявка №{num}</b>\n"
                f"👤 {full_name} (@{username})\n"
                f"🏢 {department} | 💼 {position}\n\n"
                f"📂 {data['category']}\n"
                f"📝 {text}"
            ),
            parse_mode="HTML"
        )
        for mtype, file_id in data.get("media", []):
            caption = f"📎 Медіа до заявки №{num}"
            try:
                if mtype == "photo":
                    await callback.bot.send_photo(hr_id, file_id, caption=caption)
                elif mtype == "document":
                    await callback.bot.send_document(hr_id, file_id, caption=caption)
                elif mtype == "video":
                    await callback.bot.send_video(hr_id, file_id, caption=caption)
                elif mtype == "voice":
                    await callback.bot.send_voice(hr_id, file_id, caption=caption)
            except Exception as e:
                print("Error sending media:", e)

    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        f"✅ Дякуємо, ми отримали твій запит 💬 Твоя заявка під номером №{num}. HR вже отримав сповіщення. Статус можна перевірити в головному меню. Ми розглянемо її протягом 8 робочих годин.",
        reply_markup=get_user_main_menu()
    )
    await state.clear()



@user_router.callback_query(F.data == "edit_request")
async def edit_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("📝 Введіть новий текст заявки:")
    await state.set_state(RequestState.enter_text)


@user_router.callback_query(F.data == "cancel_request")
async def cancel_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("❌ Заявку скасовано.")
    await callback.bot.send_message(
        callback.from_user.id,
        "📋 Повертаємось до меню",
        reply_markup=get_user_main_menu()
    )
    await state.clear()


async def _render_user_history(user_id: int, offset: int):
    raw_reqs = get_user_requests(user_id)
    raw_fbs = get_user_feedback(user_id)

    items = []
    for num, cat, txt, status, resp, hr_name, created, updated in raw_reqs:
        ts_str = updated or created
        ts = datetime.fromisoformat(ts_str)
        items.append(("req", (num, cat, txt, status, resp, hr_name, created, updated), ts))
    for fid, fb_text, fb_resp, created_fb, responded_at, fb_hr in raw_fbs:
        ts_str = responded_at or created_fb
        ts = datetime.fromisoformat(ts_str)
        items.append(("fb", (fid, fb_text, fb_resp, created_fb, responded_at, fb_hr), ts))

    items.sort(key=lambda x: x[2], reverse=True)

    page = items[offset: offset + PAGE_SIZE]
    if not page:
        return "📭 Немає записів на цій сторінці.", None

    parts = []
    for kind, fields, _ in page:
        if kind == "req":
            num, cat, txt, status, resp, hr_name, created, updated = fields
            parts.append(
                f"📌 <b>Заявка №{num}</b>\n"
                f"📂 Категорія: {cat}\n"
                f"📝 Текст заявки: {txt}\n"
                f"📅 Створено: {created}\n"
                f"🕒 Опрацьовано: {updated or '⏱️'}\n"
                f"📊 Статус: {status}\n"
                f"👥 HR: {hr_name or '⏳'}\n"
                f"💬 Коментар: {resp or '💤'}"
            )
        else:
            fid, fb_text, fb_resp, created_fb, responded_at, fb_hr = fields
            parts.append(
                f"🥷 <b>Анонімний відгук №{fid}</b>\n"
                f"📝 Текст відгуку: {fb_text}\n"
                f"📅 Створено: {created_fb}\n"
                f"🕒 Опрацьовано: {responded_at or '⏱️'}\n"
                f"👥 HR: {fb_hr or '⏳'}\n"
                f"💬 Коментар: {fb_resp or '💤'}"
            )

    text = "\n\n".join(parts)
    buttons = []
    total = len(items)
    if offset >= PAGE_SIZE:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Попередні",
                callback_data=f"user_history_prev_{offset - PAGE_SIZE}"
            )
        )
    if offset + PAGE_SIZE < total:
        buttons.append(
            InlineKeyboardButton(
                text="Наступні ➡️",
                callback_data=f"user_history_next_{offset + PAGE_SIZE}"
            )
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    return text, kb


@user_router.message(F.text == "📑 Перевірити статус моєї заяви")
async def my_requests(message: Message):
    text, kb = await _render_user_history(message.from_user.id, 0)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@user_router.callback_query(F.data.startswith("user_history_next_"))
async def user_history_next(cb: CallbackQuery):
    await cb.answer()
    offset = int(cb.data.rsplit("_", 1)[1])
    text, kb = await _render_user_history(cb.from_user.id, offset)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@user_router.callback_query(F.data.startswith("user_history_prev_"))
async def user_history_prev(cb: CallbackQuery):
    await cb.answer()
    offset = int(cb.data.rsplit("_", 1)[1])
    text, kb = await _render_user_history(cb.from_user.id, offset)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)



@user_router.message(F.text == "💬 Залишити анонімний відгук")
async def anonymous_feedback(message: Message, state: FSMContext):
    await message.answer(
        "✏️ Можеш вільно висловитись. Ми не бачимо, хто це написав, але ми точно звернемо увагу на це питання."
    )
    await state.set_state(FeedbackState.enter_text)


@user_router.message(FeedbackState.enter_text)
async def feedback_text_entered(message: Message, state: FSMContext):

    txt = (message.text or message.caption or "").strip()

    if not txt and not (message.photo or message.document or message.video or message.voice):
        await message.answer("⚠️ Будь ласка, напиши текст або прикріпи медіа.")
        return

    await state.update_data(fb_text=txt)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Відправити", callback_data="send_feedback"),
        InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_feedback"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_feedback"),
    ]])

    preview = f"📄 <b>Перевірте ваш анонімний відгук:</b>\n\n"
    if txt:
        preview += f"📝 {txt}"
    if message.photo or message.document or message.video or message.voice:
        preview += "\n\n📎 Додано медіа"

    await message.answer(preview, parse_mode="HTML", reply_markup=kb)


@user_router.callback_query(F.data == "send_feedback")
async def send_feedback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    fb_text = data["fb_text"]
    add_anonymous_feedback(callback.from_user.id, fb_text)
    fbs = get_new_feedback()
    fid = fbs[-1][0] if fbs else None

    for hr_id in get_all_hr_ids():
        await callback.bot.send_message(
            hr_id,
            f"💬 <b>Новий анонімний відгук №{fid}</b>\n\n{fb_text}",
            parse_mode="HTML"
        )

    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        f"✅ Дякуємо. Анонімний відгук №{fid} надіслано. Ми розглянемо його протягом 8 робочих годин. Якщо ситуація термінова — звернись до HR особисто.",
        reply_markup=get_user_main_menu()
    )
    await state.clear()


@user_router.callback_query(F.data == "edit_feedback")
async def edit_feedback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        "✏️ Введіть новий текст анонімного відгуку:"
    )


@user_router.callback_query(F.data == "cancel_feedback")
async def cancel_feedback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        "❌ Анонімний відгук скасовано.",
        reply_markup=get_user_main_menu()
    )
    await state.clear()
