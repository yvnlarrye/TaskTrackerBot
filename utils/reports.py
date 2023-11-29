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

    user_output = f"{hlink(f'{user[1]} {user[2]}', f'tg://user?id={user[0]}')} — {get_status_icon(user[3])} {user[3]}"

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
             f"<b>Заработал:</b> {earned} руб.\n\n" \
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
        telegram_id = user[1]
        user_status = user[7]
        user = (telegram_id, first_name, surname, user_status,)
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


async def format_report_data_for_table(report_id: int, author: tuple, folder_link: str):
    report = await sqlite_db.get_report_by_id(report_id)
    earned = report[2]

    done_tasks_count = 0
    if report[3]:
        done_tasks_count = len(report[3].split('\n'))

    not_done_tasks_count = 0
    if report[4]:
        not_done_tasks_count = len(report[4].split('\n'))

    scheduled_tasks_count = 0
    if report[5]:
        scheduled_tasks_count = len(report[5].split('\n'))

    username = author[3]
    surname = author[5]
    first_name = author[4]
    user_status = author[7]

    return [
        str(report_id),
        datetime.datetime.now().strftime('%d.%m.%y %H:%M'),
        str(report_id),
        f"https://t.me/{username}",
        f"{first_name} {surname}",
        f'{get_status_icon(user_status)} {user_status}',
        earned,
        folder_link,
        done_tasks_count,
        not_done_tasks_count,
        scheduled_tasks_count
    ]
