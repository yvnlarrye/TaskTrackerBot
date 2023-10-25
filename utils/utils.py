from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageToDeleteNotFound
from data import sqlite_db
from dispatcher import bot
from data.config import STATUS
import datetime


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
        result = f'{i + 1}. {surname} {first_name}'
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
    formatted_users.append('Вы можете выбрать одного или нескольких исполнителей.\n'
                           'Первый - основной исполнитель, остальные - вспомогательные.'
                           '🔵 - основной исполнитель\n'
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


async def commit_report(data: dict):
    user_id = await sqlite_db.get_user_id(data['user_id'])
    earned = data['earned']

    new_scheduled_tasks = data['new_scheduled_tasks']

    for task_description in new_scheduled_tasks:
        user_id = await sqlite_db.get_user_id(data['user_id'])
        await sqlite_db.add_scheduled_task(user_id, task_description)

    scheduled_tasks = '\n'.join(new_scheduled_tasks)
    if 'curr_tasks' in data:
        curr_tasks = data['curr_tasks']
        for task in curr_tasks:
            await sqlite_db.remove_scheduled_task_by_id(task[0])

    if 'done_tasks' in data and 'not_done_tasks' in data:
        done_tasks = data['done_tasks']
        not_done_tasks = data['not_done_tasks']
        done_tasks = '\n'.join([task[2] for task in done_tasks])
        not_done_tasks = '\n'.join([task[2] for task in not_done_tasks])
        await sqlite_db.add_report(author_id=user_id,
                                   earned=earned,
                                   done_tasks=done_tasks,
                                   not_done_tasks=not_done_tasks,
                                   scheduled_tasks=scheduled_tasks)
    else:
        await sqlite_db.add_report(author_id=user_id,
                                   earned=earned,
                                   scheduled_tasks=scheduled_tasks)


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
        case 'Red':
            return STATUS['red']['icon']
        case _:
            return STATUS['white']['icon']


def requestContainsUser(request: tuple, user: tuple) -> bool:
    telegram_id = str(user[1])

    addressers = request[3].split('\n')
    if telegram_id in addressers:
        return True

    main_recipient = request[4]
    if telegram_id == main_recipient:
        return True

    secondary_recipients = request[5].split('\n')
    if telegram_id in secondary_recipients:
        return True

    return False


async def get_user_earned_total_amount(user_id: int):
    reports = await sqlite_db.get_user_reports(user_id)
    total_amount = 0
    for report in reports:
        earned = report[2]
        total_amount += earned
    return total_amount


def curr_datetime():
    return datetime.datetime.now()


async def distribute_points(user_id: int, check_amount: int):
    status = await sqlite_db.get_user_status_by_id(user_id)

    if status == STATUS['white']['value']:
        interval = 50000
    elif status == STATUS['red']['value']:
        interval = 50000
    elif status == STATUS['silver']['value']:
        interval = 60000
    elif status == STATUS['gold']['value']:
        interval = 70000
    elif status == STATUS['diamond']['value']:
        interval = 80000
    elif status == STATUS['black']['value']:
        interval = 90000
    else:
        raise ValueError('Func got wrong user status from database')

    all_user_checks = await sqlite_db.get_user_total_check_amounts(user_id)
    current_checks_total = 0
    for check in all_user_checks:
        current_checks_total += check[0]

    remainder = current_checks_total % interval
    multiplicity = (remainder + check_amount) // interval

    if multiplicity:
        points = multiplicity * 30
        curr_points = await sqlite_db.get_user_points(user_id)
        await sqlite_db.add_points_to_user(user_id, points)
        await sqlite_db.update_user_points(user_id, curr_points + points)
        telegram_id = (await sqlite_db.get_user_by_id(user_id))[1]
        try:
            await bot.send_message(chat_id=telegram_id,
                                   text=f'Ты заработал <b>{points}</b> баллов 🎯 за очередные <b>{multiplicity * interval}</b>💰!')
        except:
            pass
