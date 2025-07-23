from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from datetime import datetime
from states import HRState, EditUserState
from keyboards.hr_keyboards import (
    get_hr_main_menu,
    get_settings_keyboard,
    get_request_action_keyboard,
    get_feedback_action_keyboard,
    get_user_list_keyboard,
    get_confirm_delete_keyboard,
    get_assign_hr_keyboard
)
from database import (
    has_hr_access,
    get_new_requests,
    get_new_feedback,
    get_processed_requests,
    get_processed_feedbacks,
    assign_hr_to_request,
    update_request_status,
    get_request,
    get_user,
    get_all_users,
    delete_user,
    update_user_info,
    generate_hr_token,
    add_feedback_response,
    add_hr,
    get_feedback_user
)

hr_router = Router()
PAGE_SIZE = 10


async def check_hr_rights(message: Message) -> bool:
    if not has_hr_access(message.from_user.id):
        await message.answer("🚫 У вас немає прав HR.")
        return False
    return True


@hr_router.message(F.text == "/hr")
async def hr_start(message: Message):
    if await check_hr_rights(message):
        await message.answer("📋 Панель HR:", reply_markup=get_hr_main_menu())


@hr_router.message(F.text == "📥 Нові заявки")
async def new_requests(message: Message):
    if not await check_hr_rights(message):
        return

    reqs = get_new_requests()
    fbs = get_new_feedback()
    if not reqs and not fbs:
        await message.answer("✅ Немає нових заявок чи відгуків.")
        return

    for req_id, num, full, dept, pos, cat, txt, created in reqs:
        user_id, _ = get_request(req_id)
        chat = await message.bot.get_chat(user_id)
        username = chat.username or "—"
        await message.answer(
            f"🆕 <b>Заявка №{req_id}</b>\n"
            f"👤 {full} (@{username})\n"
            f"🏢 {dept} | 💼 {pos}\n"
            f"📂 {cat}\n"
            f"📝 {txt}",
            parse_mode="HTML",
            reply_markup=get_request_action_keyboard(req_id)
        )

    for fid, text, created in fbs:
        await message.answer(
            f"✉️ <b>Анонімний відгук №{fid}</b>\n{text}",
            parse_mode="HTML",
            reply_markup=get_feedback_action_keyboard(fid)
        )


@hr_router.callback_query(F.data.startswith("comment_"))
async def comment_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    rid = int(callback.data.split("_")[1])
    await state.update_data(request_id=rid)
    await state.set_state(HRState.add_comment)
    await callback.message.answer(f"✏️ Введіть коментар до заявки №{rid}:")


@hr_router.message(HRState.add_comment)
async def comment_preview(message: Message, state: FSMContext):
    comment = message.text.strip()
    await state.update_data(comment=comment)
    await message.delete()

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💾 Зберегти", callback_data="save_comment"),
        InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_comment"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_comment"),
    ]])
    await message.answer(
        f"📄 <b>Перевірте коментар:</b>\n\n{comment}",
        parse_mode="HTML",
        reply_markup=kb
    )


@hr_router.callback_query(F.data == "save_comment")
async def save_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    rid = data["request_id"]
    comment = data["comment"]

    assign_hr_to_request(rid, callback.from_user.id)
    update_request_status(rid, None, comment)

    user_id, _ = get_request(rid)
    await callback.bot.send_message(
        user_id,
        f"💬 HR додав коментар до вашої заявки №{rid}:\n{comment}"
    )

    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        f"✅ Коментар збережено. Тепер схваліть або відхиліть заявку №{rid}.",
        reply_markup=get_hr_main_menu()
    )
    await state.clear()


@hr_router.callback_query(F.data == "edit_comment")
async def edit_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("✏️ Введіть новий коментар до заявки:")
    await state.set_state(HRState.add_comment)


@hr_router.callback_query(F.data == "cancel_comment")
async def cancel_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        "❌ Коментар до заявки скасовано.",
        reply_markup=get_hr_main_menu()
    )
    await state.clear()


async def _render_hr_history(bot, offset: int):
    raw_reqs = get_processed_requests(limit=None)
    raw_fbs = get_processed_feedbacks(limit=None)

    items = []
    for r in raw_reqs:
        ts_str = r[10] or r[9]
        ts = datetime.fromisoformat(ts_str)
        items.append(("req", r, ts))
    for f in raw_fbs:
        ts_str = f[4] or f[3]
        ts = datetime.fromisoformat(ts_str)
        items.append(("fb", f, ts))
    items.sort(key=lambda x: x[2], reverse=True)

    page = items[offset : offset + PAGE_SIZE]
    if not page:
        return "📭 Немає оброблених записів на цій сторінці.", None

    parts = []
    for kind, fields, _ in page:
        if kind == "req":
            (_id, num, full, dept, pos, cat, txt,
             status, resp, created, updated, hr_name) = fields
            user_id, _ = get_request(_id)
            chat = await bot.get_chat(user_id)
            username = chat.username or "—"
            symbol = "✅" if status == "Схвалено" else "❌" if status == "Відхилено" else ""
            parts.append(
                f"📌 <b>Заявка №{_id}</b>\n"
                f"👤 ПІБ: {full} (@{username})\n"
                f"🏢 Відділ: {dept}\n"
                f"💼 Посада: {pos}\n"
                f"📂 Категорія: {cat}\n"
                f"📝 Текст звернення: {txt}\n"
                f"📅 Створено: {created}\n"
                f"🕒 Опрацьовано: {updated or '⏱️'}\n"
                f"👥 HR: {hr_name or '⏳'}\n"
                f"💬 Коментар: {resp or '—'}\n"
                f"📊 Результат: {symbol}{status}"
            )
        else:
            fid, fb_text, fb_response, created_fb, responded_at, fb_hr = fields
            parts.append(
                f"🥷 <b>Анонімний відгук №{fid}</b>\n"
                f"📝 {fb_text}\n"
                f"📅 Створено: {created_fb}\n"
                f"🕒 Опрацьовано: {responded_at or '⏱️'}\n"
                f"👥 HR: {fb_hr or '⏳'}\n"
                f"💬 Відповідь HR: {fb_response or '—'}"
            )

    text = "\n\n".join(parts)
    total = len(items)

    buttons = []
    if offset >= PAGE_SIZE:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Попередні",
                callback_data=f"hr_history_prev_{offset - PAGE_SIZE}"
            )
        )
    if offset + PAGE_SIZE < total:
        buttons.append(
            InlineKeyboardButton(
                text="Наступні ➡️",
                callback_data=f"hr_history_next_{offset + PAGE_SIZE}"
            )
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    return text, kb


@hr_router.message(F.text == "📜 Історія заявок")
async def hr_history(message: Message):
    if not await check_hr_rights(message):
        return
    text, kb = await _render_hr_history(message.bot, 0)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@hr_router.callback_query(F.data.startswith("hr_history_next_"))
async def hr_history_next(cb: CallbackQuery):
    await cb.answer()
    offset = int(cb.data.split("_")[-1])
    text, kb = await _render_hr_history(cb.bot, offset)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@hr_router.callback_query(F.data.startswith("hr_history_prev_"))
async def hr_history_prev(cb: CallbackQuery):
    await cb.answer()
    offset = int(cb.data.split("_")[-1])
    text, kb = await _render_hr_history(cb.bot, offset)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@hr_router.callback_query(F.data.startswith("approve_"))
async def approve_request(callback: CallbackQuery):
    await callback.answer()
    req_id = int(callback.data.split("_")[-1])
    assign_hr_to_request(req_id, callback.from_user.id)
    update_request_status(req_id, "✅ Схвалено", None)
    user_id, _ = get_request(req_id)

    await callback.message.delete()
    await callback.bot.send_message(
        user_id,
        f"✅ Ваша заявка №{req_id} схвалена."
    )
    await callback.bot.send_message(
        callback.from_user.id,
        f"✅ Заявку №{req_id} опрацьовано та схвалено.",
        reply_markup=get_hr_main_menu()
    )


@hr_router.callback_query(F.data.startswith("reject_"))
async def reject_request(callback: CallbackQuery):
    await callback.answer()
    req_id = int(callback.data.split("_")[-1])
    assign_hr_to_request(req_id, callback.from_user.id)
    update_request_status(req_id, "❌ Відхилено", None)
    user_id, _ = get_request(req_id)

    await callback.message.delete()
    await callback.bot.send_message(
        user_id,
        f"❌ Ваша заявка №{req_id} відхилена."
    )
    await callback.bot.send_message(
        callback.from_user.id,
        f"❌ Заявку №{req_id} опрацьовано та відхилено.",
        reply_markup=get_hr_main_menu()
    )


@hr_router.callback_query(F.data.startswith("reply_feedback_"))
async def ask_feedback_reply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    fid = int(callback.data.split("_")[-1])
    await state.update_data(
        feedback_id=fid,
        fb_chat_id=callback.message.chat.id,
        fb_msg_id=callback.message.message_id
    )
    await state.set_state(HRState.reply_feedback)
    await callback.message.answer(f"✏️ Введіть відповідь на анонімний відгук №{fid}:")


@hr_router.message(HRState.reply_feedback)
async def feedback_reply_entered(message: Message, state: FSMContext):
    resp = message.text.strip()
    await state.update_data(response=resp)
    await message.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Відправити", callback_data="send_feedback_reply"),
        InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_feedback_reply"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_feedback_reply"),
    ]])
    await message.answer(
        f"📄 <b>Перевірте відповідь:</b>\n\n💬 {resp}",
        parse_mode="HTML",
        reply_markup=kb
    )


@hr_router.callback_query(F.data == "send_feedback_reply")
async def send_feedback_reply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    fid = data["feedback_id"]
    resp = data["response"]
    add_feedback_response(fid, resp, callback.from_user.id)
    user_id = get_feedback_user(fid)

    await callback.bot.delete_message(data["fb_chat_id"], data["fb_msg_id"])
    await callback.message.delete()

    if user_id:
        await callback.bot.send_message(
            user_id,
            f"📣 У вашому відгуку №{fid} відповідь:\n{resp}"
        )
    await callback.bot.send_message(
        callback.from_user.id,
        f"✅ Відгук №{fid} оброблено.",
        reply_markup=get_hr_main_menu()
    )
    await state.clear()


@hr_router.callback_query(F.data == "edit_feedback_reply")
async def edit_feedback_reply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("✏️ Введіть нову відповідь:")


@hr_router.callback_query(F.data == "cancel_feedback_reply")
async def cancel_feedback_reply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.bot.send_message(
        callback.from_user.id,
        "❌ Обробку відгуку скасовано.",
        reply_markup=get_hr_main_menu()
    )
    await state.clear()


@hr_router.message(F.text == "👥 Співробітники")
async def show_users(message: Message):
    if not await check_hr_rights(message):
        return
    users = get_all_users()
    if not users:
        await message.answer("🔍 Користувачів не знайдено.")
        return
    prepared = [(u[0], u[1], u[2], u[3]) for u in users]
    await message.answer("👥 Співробітники:", reply_markup=get_user_list_keyboard(prepared))


@hr_router.message(F.text == "⚙️ Налаштування")
async def hr_settings(message: Message):
    if not await check_hr_rights(message):
        return
    await message.answer("⚙️ Меню Налаштування:", reply_markup=get_settings_keyboard())


@hr_router.message(F.text == "Призначити HR")
async def assign_hr_menu(message: Message):
    if not await check_hr_rights(message):
        return
    users = get_all_users()
    prepared = [(u[0], u[1], u[2], u[3]) for u in users]
    await message.answer(
        "👥 Оберіть користувача для призначення HR:",
        reply_markup=get_assign_hr_keyboard(prepared)
    )


@hr_router.message(F.text == "Назад")
async def settings_back(message: Message):
    if not await check_hr_rights(message):
        return
    await message.answer("📋 Панель HR:", reply_markup=get_hr_main_menu())


@hr_router.message(F.text == "🔑 Згенерувати токен HR")
async def generate_token(message: Message):
    if not await check_hr_rights(message):
        return
    token = generate_hr_token()
    await message.answer(f"🔐 Ваш HR-токен:\n<code>{token}</code>", parse_mode="HTML")


@hr_router.callback_query(F.data.startswith("assign_hr_"))
async def assign_hr_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    row = get_user(user_id)
    full_name = row[1] if row else str(user_id)

    add_hr(user_id)

    await callback.bot.send_message(
        user_id,
        "🎉 Вітаємо, вас призначено HR! Перезапустіть бота для оновлення функціоналу."
    )
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        f"Співробітника «{full_name}» було призначено HR.",
        reply_markup=get_hr_main_menu()
    )


@hr_router.callback_query(F.data.startswith("delete_user_"))
async def ask_delete_user(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    await callback.message.edit_text(
        "❗️ Ви впевнені?",
        reply_markup=get_confirm_delete_keyboard(user_id)
    )


@hr_router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])

    row = get_user(user_id)
    full_name = row[1] if row else str(user_id)

    delete_user(user_id)
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        f"Співробітника «{full_name}» було видалено.",
        reply_markup=get_hr_main_menu()
    )


@hr_router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        "❌ Скасовано.",
        reply_markup=get_hr_main_menu()
    )


@hr_router.callback_query(F.data.startswith("edit_user_"))
async def edit_user(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(user_id=user_id)
    await state.set_state(EditUserState.waiting_full_name)
    await callback.message.answer("✏️ Введіть новий ПІБ:")


@hr_router.message(EditUserState.waiting_full_name)
async def update_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(EditUserState.waiting_department)
    await message.answer("🏢 Введіть відділ:")


@hr_router.message(EditUserState.waiting_department)
async def update_department(message: Message, state: FSMContext):
    await state.update_data(department=message.text.strip())
    await state.set_state(EditUserState.waiting_position)
    await message.answer("💼 Введіть посаду:")


@hr_router.message(EditUserState.waiting_position)
async def update_position(message: Message, state: FSMContext):
    data = await state.get_data()
    update_user_info(
        data["user_id"],
        data["full_name"],
        data["department"],
        message.text.strip()
    )
    await message.answer(
        "✅ Оновлено.",
        reply_markup=get_hr_main_menu()
    )
    await state.clear()
