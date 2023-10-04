from aiogram.dispatcher.filters.state import StatesGroup, State


class SessionRole(StatesGroup):
    admin = State()
    member = State()
    general = State()


class UserEdition(StatesGroup):
    new_admin_name = State()
    admin = State()
    admin_name = State()
    admin_surname = State()
    member = State()
    member_first_name = State()
    member_surname = State()
    ask_make_admin = State()
    remove_member = State()


class CreateRequest(StatesGroup):
    request_from = State()
    request_to = State()
    text = State()
    date = State()
    time = State()


class EditRequest(StatesGroup):
    ask_confirm_removing = State()
    remove = State()
    time = State()
    date = State()
    edit = State()
    select_member_request = State()
    select_request_headers = State()
    status = State()
    addressers = State()
    recipients = State()
    text = State()


class CreateReport(StatesGroup):
    scheduled_tasks = State()
    not_done_tasks = State()
    done_tasks = State()
    earned = State()
    list_of_done_tasks = State()
    list_of_not_done_tasks = State()
    list_of_scheduled_tasks = State()


class EditReport(StatesGroup):
    list_of_scheduled_tasks = State()
    list_of_not_done_tasks = State()
    list_of_done_tasks = State()
    phone_time = State()
    select_report_headers = State()
    edit_by_admin = State()
    select_member_report = State()


class Channel(StatesGroup):
    listening_request_channel = State()
    listening_report_channel = State()
    choose = State()


class Points(StatesGroup):
    add = State()
    add_amount = State()
    reduce = State()
    reduce_amount = State()
