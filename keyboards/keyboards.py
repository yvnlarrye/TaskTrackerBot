from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from utils.utils import formatted_users_list, __toggle_btn, __toggle_main_recipients_btn
from utils.request import request_status_str
from data.config import STATUS, CONFIG
from aiogram.utils.markdown import hlink

intro_admin_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('👨‍💻 Участник'),
    KeyboardButton('🏴‍☠️ Админ')
).add(
    KeyboardButton('🏆📈 Топы')
)

# .add(
#     KeyboardButton('TEST_DAILY'),
#     KeyboardButton('TEST_WEEKLY'),
#     KeyboardButton('TEST_MONTHLY'),
# )

intro_member_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('👨‍💻 Участник')
).add(
    KeyboardButton('🏆📈 Топы'),
)

member_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('📝 Запрос'),
    KeyboardButton('📩 Отчетность')
).add(
    KeyboardButton('✏️ Ред. запрос')
    # KeyboardButton('✏️ Ред. отчётность')
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
).add(
    KeyboardButton('↩️ Вернуться назад')
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
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


async def users_requests_kb(requests: list):
    requests_ids = [f'Запрос #{req[0]} {request_status_str(req[2])[0]}' for req in requests]
    return __list_of_elements_kb(requests_ids)


async def request_headers_kb():
    headers = ['Статус', 'От кого', 'Кому', 'Запрос', 'Срок']
    return __list_of_elements_kb(headers)


async def request_status_kb():
    statuses = ['❌ — Не выполнено', '🔄 — В процессе', '✅ — Выполнено']
    return __list_of_elements_kb(statuses)


async def user_status_kb():
    statuses = [f"{STATUS[key]['icon']} - {STATUS[key]['value']}" for key in STATUS.keys()]
    return __list_of_elements_kb(statuses)


def apply_tasks_kb():
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text='Подтвердить', callback_data='apply_tasks'),
        InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
    )
    return keyboard


async def member_reports_kb(reports: list):
    reports_ids = [f'Отчёт #{req[0]}' for req in reports]
    return __list_of_elements_kb(reports_ids)


async def report_headers_kb():
    headers = [
        'Заработано 💰',
        'Выполненные задачи ✅',
        'Невыполненные задачи ❌',
        'Запланированные задачи 📝'
    ]
    return __list_of_elements_kb(headers)

permission_denied_message = f'Привет! Рад, что ты теперь с нами!\n\n' \
                            f'Это закрытое сообщество <b>«Нельзя, Но Можно»</b> и здесь ты точно достигнешь всех своих целей! 🚀\n\n' \
                            f'Для того, чтобы состоять в нашем сообществе, тебе необходимо подписаться на следующие каналы и чаты:\n\n' \
                            f'🤖 {hlink("Бот-ассистент", "https://t.me/nobutyesteam_bot")} — он поможет тебе заполнить ежедневную отчетность, оставить запрос другим участникам, закрывать цели, следить за статистикой своей и других участников\n' \
                            f'💬 {hlink("Общий чат", "https://t.me/+1tq1Vrx7chNkNGQy")} — для ежедневного общения с участниками\n' \
                            f'📝 {hlink("Ежедневные задачи", "https://t.me/+bHfggUwLTfQzZTUy")} — здесь отображаются ваши задачи за прошедший день и на следующий\n' \
                            f'📝 {hlink("Отчеты", "https://t.me/+_fm9utI7EW82OWJi")} — статистика участников за день/неделю/месяц\n' \
                            f'🎯 {hlink("Закрытые цели", "https://t.me/+IOhfgXR3dcEzODli")} — здесь публикуются все закрытые цели участников\n' \
                            f'⚙️ {hlink("База знаний", "https://t.me/+dei2b--LBsJhMmIy")} — тут можешь найти разработанные для инфобиза таблицы, необходимые обучения, ответ на свой \n' \
                            f'📝 {hlink("Запросы", "https://t.me/+SgHj8E-IpHMxZWUy")} — оставляй любой запрос участникам сообщества\n\n' \
                            f'❗️Теперь объедини все каналы и чаты в одну папку, чтобы тебе было удобно. Как это сделать — {hlink("смотреть видео", "https://drive.google.com/file/d/1kyGfO5XPBReBcARjKgBGZK9lnOHOTQaD/view?usp=drive_link")} ❗️'


check_subscribes_kb = InlineKeyboardMarkup().add(
   InlineKeyboardButton(text='Проверить подписки', callback_data='check_subscribes')
)


def scheduled_tasks_kb(tasks: list, marked_tasks_indices: list = None):
    buttons_list = []

    formatted_tasks = [tasks[i][2] for i in range(len(tasks))]

    for i in range(len(formatted_tasks)):
        if marked_tasks_indices and i in marked_tasks_indices:
            formatted_tasks[i] += '🔴'
        buttons_list.append([InlineKeyboardButton(text=formatted_tasks[i], callback_data=f'task_{i}')])
    buttons_list.append([InlineKeyboardButton(text='Далее⏩', callback_data='next_step')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)


def hashtag_kb(marked_indices: list = None):
    buttons_list = []
    button_row = []
    hashtag_names = [hashtag['name'] for hashtag in CONFIG['hashtags']]

    for i in range(len(hashtag_names)):
        if marked_indices and i in marked_indices:
            hashtag_names[i] += '🔴'
        button_row.append(InlineKeyboardButton(text=hashtag_names[i], callback_data=f'task_{i}'))
        if (i % 2 != 0) or (i == len(hashtag_names) - 1):
            buttons_list.append(button_row)
            button_row = []
    buttons_list.append([InlineKeyboardButton(text='✅ Подтвердить', callback_data='next_step')])
    buttons_list.append([InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')])
    return InlineKeyboardMarkup(inline_keyboard=buttons_list)
