from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageCantBeDeleted
from data import sqlite_db
from dispatcher import bot
from data.config import STATUS, CONFIG, REQUEST_STATUS
import datetime

from google.sheet_manager import append_row_in_table


async def is_admin(telegram_id: int) -> bool:
    user_id = await sqlite_db.get_user_id(telegram_id)
    role = await sqlite_db.get_user_role(user_id)
    if role == 1:
        return True
    if role == 0:
        return False
    raise ValueError


def request_status_str(request_status: int):
    if request_status == 0:
        return REQUEST_STATUS['not_done']
    elif request_status == 1:
        return REQUEST_STATUS['in_progress']
    elif request_status == 2:
        return REQUEST_STATUS['done']
    else:
        raise AttributeError


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

    done_tasks = None
    not_done_tasks = None

    if 'done_tasks' in data:
        done_tasks = data['done_tasks']
        done_tasks = '\n'.join([task[2] for task in done_tasks])
    if 'not_done_tasks' in data:
        not_done_tasks = data['not_done_tasks']
        not_done_tasks = '\n'.join([task[2] for task in not_done_tasks])

    await sqlite_db.add_report(author_id=user_id,
                               earned=earned,
                               done_tasks=done_tasks,
                               not_done_tasks=not_done_tasks,
                               scheduled_tasks=scheduled_tasks)


async def delete_prev_message(chat_id, state: FSMContext):
    data = await state.get_data()
    if 'msg' in data:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=data['msg'].message_id)
        except (MessageToDeleteNotFound, MessageCantBeDeleted):
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

    if telegram_id == request[4]:
        return True

    if telegram_id == request[5]:
        return True

    return False


def is_user_recipient(request: tuple, user: tuple) -> bool:
    telegram_id = str(user[1])
    if telegram_id == request[4]:
        return True
    if telegram_id == request[5]:
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
        comment = 'закрытая цель'
        await sqlite_db.add_points_to_user(user_id, points, comment)
        await sqlite_db.update_user_points(user_id, curr_points + points)

        record_id = await sqlite_db.get_user_last_points_record_id(user_id)
        row_data = await format_points_data_for_table(record_id, user_id, points, None, comment)

        append_row_in_table(table_name=CONFIG['points_sheet_name'],
                            row_range='A:H',
                            values=[row_data])
        telegram_id = (await sqlite_db.get_user_by_id(user_id))[1]
        try:
            await bot.send_message(chat_id=telegram_id,
                                   text=f'Ты заработал <b>{points}</b> баллов 🎯 за очередные <b>{multiplicity * interval}</b>💰!')
        except:
            pass


async def format_goal_data_for_table(author: tuple, shared_link: str):
    goal_id = await sqlite_db.get_user_last_goal_id(author[0])
    goal = await sqlite_db.get_goal_by_id(goal_id)
    username = author[3]
    surname = author[5]
    first_name = author[4]
    user_status = author[7]
    notion_link = goal[2]
    check_amount = goal[3]
    comment = goal[4]

    return [
        str(goal_id),
        datetime.datetime.now().strftime('%d.%m.%y %H:%M'),
        f"https://t.me/{username}",
        f"{first_name} {surname}",
        f'{get_status_icon(user_status)} {user_status}',
        notion_link,
        check_amount,
        comment,
        shared_link
    ]


async def format_points_data_for_table(record_id: int,
                                       user_id: int,
                                       add_points_amount: float | None,
                                       reduce_points_amount: float | None,
                                       comment: str):

    user = await sqlite_db.get_user_by_id(user_id)

    username = user[3]
    surname = user[5]
    first_name = user[4]
    user_status = user[7]

    return [
        str(record_id),
        datetime.datetime.now().strftime('%d.%m.%y %H:%M'),
        f"https://t.me/{username}",
        f"{first_name} {surname}",
        f'{get_status_icon(user_status)} {user_status}',
        add_points_amount,
        reduce_points_amount,
        comment
    ]
