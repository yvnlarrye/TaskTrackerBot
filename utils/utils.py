from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageToDeleteNotFound

from data import sqlite_db
from dispatcher import bot
from states import SessionRole
from data.config import STATUS


async def is_admin(telegram_id: int) -> bool:
    user_id = await sqlite_db.get_user_id(telegram_id)
    role = await sqlite_db.get_user_role(user_id)
    if role == 1:
        return True
    if role == 0:
        return False
    raise ValueError


def formatted_users_list(users: list):
    formatted_users = []
    for i, user in enumerate(users):
        surname = user[5]
        first_name = user[4]
        username = user[3]
        result = f'{i + 1}. {surname} {first_name} @{username}'
        formatted_users.append(result)
    return formatted_users


async def format_addressers(users: list, users_indices: list = None):
    formatted_users = formatted_users_list(users)
    if users_indices:
        for i, user_index in enumerate(users_indices):
            formatted_users[user_index] = formatted_users[user_index] + ' 🟢'
    formatted_users.insert(0, '<b>Выберите от кого отправляется запрос:</b>')
    return '\n\n'.join(formatted_users)


async def format_recipients(users: list, users_indices: list = None):
    formatted_users = formatted_users_list(users)
    if users_indices:
        for i, user_index in enumerate(users_indices):
            if i == 0:
                formatted_users[user_index] = formatted_users[user_index] + ' 🔵'
            else:
                formatted_users[user_index] = formatted_users[user_index] + ' 🟢'
    formatted_users.insert(0, '<b>Выберите, кому отправляется запрос:</b>')
    formatted_users.append('🔵 - основной исполнитель\n'
                           '🟢 - вспомогательные исполнители')
    return '\n\n'.join(formatted_users)


def __toggle_btn(btn_text: str):
    text = btn_text
    if '🟢' in btn_text:
        text = btn_text.replace('🟢', '🔴')
    elif '🔴' in btn_text:
        text = btn_text.replace('🔴', '🟢')
    return text


def __toggle_main_recipients_btn(btn_text: str):
    text = btn_text
    if '🔴' in btn_text:
        text = btn_text.replace('🔴', '🔵')
    return text


def __toggle_remove_member(btn_text: str):
    text = btn_text
    if '🔴' not in text:
        text = text + '🔴'
    else:
        text = text.replace('🔴', '')
    return text


async def refresh_role(state: FSMContext):
    data = await state.get_data()
    role_state = data['role_state']
    await state.finish()
    if role_state == 'admin':
        await SessionRole.admin.set()
    elif role_state == 'member':
        await SessionRole.member.set()


async def commit_report(data: dict):
    author_id = await sqlite_db.get_user_id(data['user_id'])
    earned = data['earned']
    done_tasks = '\n'.join(data['done_tasks_list'])
    not_done_tasks = '\n'.join(data['not_done_tasks_list'])
    scheduled_tasks = '\n'.join(data['scheduled_tasks_list'])
    await sqlite_db.add_report(author_id, earned, done_tasks, not_done_tasks, scheduled_tasks)


async def delete_prev_message(chat_id, state: FSMContext):
    data = await state.get_data()
    if 'msg' in data:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=data['msg'].message_id)
        except MessageToDeleteNotFound:
            pass


def get_status_icon(status: str):
    match status:
        case 'Silver':
            return STATUS['silver']['icon']
        case 'Gold':
            return STATUS['gold']['icon']
        case 'Diamond':
            return STATUS['diamond']['icon']
        case 'Black':
            return STATUS['black']['icon']
        case _:
            return STATUS['white']['icon']


def requestContainsUser(request: tuple, user: tuple) -> bool:
    username = user[3]

    addressers = request[3].split('\n')
    if username in addressers:
        return True

    main_recipient = request[4]
    if username == main_recipient:
        return True

    secondary_recipients = request[5].split('\n')
    if username in secondary_recipients:
        return True

    return False

