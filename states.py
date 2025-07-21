from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    token = State()
    full_name = State()
    department = State()
    position = State()


class RequestState(StatesGroup):
    choose_category = State()
    enter_text = State()
    confirm = State()


class FeedbackState(StatesGroup):
    enter_text = State()


class HRState(StatesGroup):
    add_comment = State()
    reply_feedback = State()
    waiting_hr_username = State()


class EditUserState(StatesGroup):
    waiting_full_name = State()
    waiting_department = State()
    waiting_position = State()
