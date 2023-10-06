from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from utils.utils import formatted_users_list, __toggle_btn, __toggle_main_recipients_btn
from utils.request import request_status_str
from data.config import STATUS

intro_admin_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('👨‍💻 Участник'),
    KeyboardButton('☠️ Админ')
).add(
    KeyboardButton('🏆📈 Топы'),
)

intro_member_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('👨‍💻 Участник')
).add(
    KeyboardButton('🏆📈 Топы'),
)

member_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('📝 Запрос'),
    KeyboardButton('📩 Отчетность')
).add(
    KeyboardButton('✏️ Ред. запрос'),
    KeyboardButton('✏️ Ред. отчётность')
).add(
    KeyboardButton('✅ Закрытые цели')
).add(
    KeyboardButton('🏠 Выйти')
)

admin_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('✅ Добавить участника'),
    KeyboardButton('✅ Добавить админа')
).add(
    KeyboardButton('📊 Баллы'),
    KeyboardButton('👑 Изменить статус')
).add(
    KeyboardButton('⛔👨‍💻 Удалить участника'),
    KeyboardButton('⛔📝 Удалить запрос')
).add(
    KeyboardButton('🏠 Выйти'),
    KeyboardButton('↪️ Каналы')
)

points_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('📊 Начислить баллы'),
    KeyboardButton('🚫 Отнять баллы')
)

channels_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='📝 Запросы', callback_data='edit_request_channel')
).add(
    InlineKeyboardButton(text='📩 Отчетность', callback_data='edit_report_channel')
).add(
    InlineKeyboardButton(text='✅ Цели', callback_data='edit_goals_channel')
).add(
    InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
)

cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('🏠Выйти')
)

prev_step_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
)
prev_step_reply_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('↩️ Вернуться назад')
)

approve_promotion_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='Да', callback_data='approve_prom'),
    InlineKeyboardButton(text='Нет', callback_data='refuse_prom')
)

approve_removing_request_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='✅ Подтвердить', callback_data='approve_rem_req'),
    InlineKeyboardButton(text='❌ Отмена', callback_data='cancel_rem_req')
)


async def remove_member_kb(curr_users: list, member_index=None):
    buttons_list = []
    formatted_users = formatted_users_list(curr_users)
    for i in range(len(formatted_users)):
        if i == member_index:
            formatted_users[i] = formatted_users[i] + '🔴'
        buttons_list.append([InlineKeyboardButton(text=formatted_users[i], callback_data=f'rm_user_{i}')])
    buttons_list.append([InlineKeyboardButton(text='❌ Удалить участника', callback_data='approve_remove')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


async def select_member_to_edit_status_kb(curr_users: list, member_index=None):
    buttons_list = []
    formatted_users = formatted_users_list(curr_users)
    for i in range(len(formatted_users)):
        if i == member_index:
            formatted_users[i] = formatted_users[i] + '🔴'
        buttons_list.append([InlineKeyboardButton(text=formatted_users[i], callback_data=f'user_{i}')])
    buttons_list.append([InlineKeyboardButton(text='Далее ⏩', callback_data='next_step')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


async def update_addressers_kb(curr_users: list, marked_members: list = None, cols=5):
    buttons_list = []
    button_row = []
    for i in range(len(curr_users)):
        btn_text = f'🔴{i + 1}'
        if marked_members:
            if i in marked_members:
                button_row.append(InlineKeyboardButton(text=__toggle_btn(btn_text), callback_data=f'user_{i}'))
            else:
                button_row.append(InlineKeyboardButton(text=btn_text, callback_data=f'user_{i}'))
        else:
            button_row.append(InlineKeyboardButton(text=btn_text, callback_data=f'user_{i}'))
        if (i != 0 and i % (cols - 1) == 0) or i == len(curr_users) - 1:
            buttons_list.append(button_row)
            button_row = []
    buttons_list.append([InlineKeyboardButton(text='Далее⏩', callback_data='next_step')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


async def update_recipients_kb(curr_users: list, user_indices: list = None, cols=5):
    buttons_list = []
    button_row = []
    for i in range(len(curr_users)):
        btn_text = f'🔴{i + 1}'
        if user_indices:
            if i in user_indices:
                if user_indices[0] == i:
                    button_row.append(InlineKeyboardButton(text=__toggle_main_recipients_btn(btn_text),
                                                           callback_data=f'user_{i}'))
                else:
                    button_row.append(InlineKeyboardButton(text=__toggle_btn(btn_text), callback_data=f'user_{i}'))

            else:
                button_row.append(InlineKeyboardButton(text=btn_text, callback_data=f'user_{i}'))
        else:
            button_row.append(InlineKeyboardButton(text=btn_text, callback_data=f'user_{i}'))
        if (i != 0 and i % (cols - 1) == 0) or i == len(curr_users) - 1:
            buttons_list.append(button_row)
            button_row = []
    buttons_list.append([InlineKeyboardButton(text='Далее⏩', callback_data='next_step')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


async def update_users_to_update_points(curr_users: list, marked_members_indices: list = None):
    buttons_list = []
    formatted_users = formatted_users_list(curr_users)
    for i in range(len(formatted_users)):
        if marked_members_indices and i in marked_members_indices:
            formatted_users[i] += '🔴'
        buttons_list.append([InlineKeyboardButton(text=formatted_users[i], callback_data=f'user_{i}')])
    buttons_list.append([InlineKeyboardButton(text='Далее⏩', callback_data='next_step')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


def __list_of_elements_kb(elements: list):
    buttons_list = []
    for i, elm in enumerate(elements):
        buttons_list.append([InlineKeyboardButton(text=elm, callback_data=f'elm_{i}')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


async def users_requests_kb(requests: list):
    requests_ids = [f'Запрос #{req[0]} {request_status_str(req[2])[0]}' for req in requests]
    return __list_of_elements_kb(requests_ids).add(
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )


async def request_headers_kb():
    headers = ['Статус', 'От кого', 'Кому', 'Запрос', 'Срок']
    return __list_of_elements_kb(headers).add(
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )


async def request_status_kb():
    statuses = ['❌ — Не выполнено', '🔄 — В процессе', '✅ — Выполнено']
    return __list_of_elements_kb(statuses).add(
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )


async def user_status_kb():
    statuses = [f"{STATUS[key]['icon']} - {STATUS[key]['value']}" for key in STATUS.keys()]
    return __list_of_elements_kb(statuses).add(
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )


def apply_tasks_kb():
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text='Подтвердить', callback_data='apply_tasks'),
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )
    return keyboard


async def member_reports_kb(reports: list):
    reports_ids = [f'Отчёт #{req[0]}' for req in reports]
    return __list_of_elements_kb(reports_ids).add(
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )


async def report_headers_kb():
    headers = [
        'Заработано 💰',
        'Выполненные задачи ✅',
        'Невыполненные задачи ❌',
        'Запланированные задачи 📝'
    ]
    return __list_of_elements_kb(headers).add(
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )
