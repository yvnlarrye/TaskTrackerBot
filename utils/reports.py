import datetime

from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.exceptions import ChatNotFound, MessageIdInvalid, MessageToEditNotFound

from data import sqlite_db
from data.config import CONFIG
from dispatcher import bot
from aiogram.utils.markdown import hlink

from utils.utils import get_status_icon

from keyboards import keyboards as kb


async def print_report(report_id: int, user: tuple, earned: str,
                       scheduled_tasks: list, done_tasks: list = None, not_done_tasks: list = None):
    today = datetime.date.today()
    today_str = today.strftime("%d.%m.%Y")
    tomorrow = (today + datetime.timedelta(days=1)).strftime("%d.%m.%Y")

    user_output = f"{get_status_icon(user[3])} {hlink(f'{user[1]} {user[2]}', f'https://t.me/{user[0]}')} — {user[3]}"

    done_tasks_output = ''
    if done_tasks is not None:
        done_tasks_output = '✅<b>Выполнено</b>\n\n' + '\n'.join(['- ' + task for task in done_tasks]) + '\n\n'

    not_done_tasks_output = ''
    if not_done_tasks is not None:
        not_done_tasks_output = '❌<b>Не выполнено</b>\n\n' + '\n'.join(['- ' + task for task in not_done_tasks]) + '\n\n'

    scheduled_tasks = '\n'.join(['- ' + task for task in scheduled_tasks])
    result = f"Отчёт #{report_id}\n\n" \
             f"{user_output}\n\n" \
             f"<b>Дата:</b> {today_str}\n\n" \
             f"<b>Заработал:</b> - {earned} руб.\n\n" \
             f"{done_tasks_output}" \
             f"{not_done_tasks_output}" \
             f"📝<b>План на</b> - {tomorrow}\n\n" \
             f"{scheduled_tasks}"
    return result


async def update_report_message(report_id: int):
    try:
        curr_report = await sqlite_db.get_report_by_id(report_id)

        user = await sqlite_db.get_user_by_id(curr_report[1])

        surname = user[5]
        first_name = user[4]
        user_name = user[3]
        user_status = user[7]
        user = (user_name, first_name, surname, user_status,)
        earned = curr_report[2]
        done_tasks = curr_report[3]
        if done_tasks:
            done_tasks = curr_report[3].split('\n')
        not_done_tasks = curr_report[4]
        if not_done_tasks:
            not_done_tasks = curr_report[4].split('\n')
        scheduled_tasks = curr_report[5].split('\n')
        message_id = curr_report[6]

        new_output = await print_report(report_id=report_id,
                                        user=user,
                                        earned=earned,
                                        done_tasks=done_tasks,
                                        not_done_tasks=not_done_tasks,
                                        scheduled_tasks=scheduled_tasks)

        await bot.edit_message_text(text=new_output, chat_id=CONFIG['channels']['report_channel'], message_id=message_id)
    except (MessageToEditNotFound, MessageIdInvalid, ChatNotFound):
        await sqlite_db.remove_report_by_id(report_id)


async def update_selected_done_tasks(cb: CallbackQuery, state: FSMContext, text: str):
    user_index = int(cb.data[5:])

    data = await state.get_data()
    if 'done_tasks_indices' not in data:
        await state.update_data(done_tasks_indices=[])

    data = await state.get_data()
    tasks_indices = data['done_tasks_indices']

    if user_index in tasks_indices:
        tasks_indices.remove(user_index)
    else:
        tasks_indices.append(user_index)
    await state.update_data(done_tasks_indices=tasks_indices)
    tasks = data['curr_tasks']
    new_keyboard = kb.scheduled_tasks_kb(tasks, tasks_indices)
    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=text,
                                reply_markup=new_keyboard)


async def report_tracker():
    users = await sqlite_db.get_users()
    for user in users:
        user_id = user[0]
        user_reports_count = await sqlite_db.count_user_reports_per_day(user_id)

        points_amount = 1 if user_reports_count else -1
        user_points = await sqlite_db.get_user_points(user_id)
        user_points += points_amount
        await sqlite_db.add_points_to_user(user_id, points_amount)

        await sqlite_db.update_user_points(user_id, user_points)


