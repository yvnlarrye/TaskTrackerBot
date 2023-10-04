import datetime
import json
from data import sqlite_db
from data.config import CONFIG
from dispatcher import bot
from utils.utils import get_json_file_contents
from aiogram.utils.markdown import hlink


async def print_report(report_id: int, surname: str, first_name: str, username: str, earned: str,
                       done_tasks: list, not_done_tasks: list, scheduled_tasks: list):
    today = datetime.date.today()
    today_str = today.strftime("%d.%m.%Y")
    tomorrow = (today + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    done_tasks = '\n'.join(['- ' + task for task in done_tasks])
    not_done_tasks = '\n'.join(['- ' + task for task in not_done_tasks])
    scheduled_tasks = '\n'.join(['- ' + task for task in scheduled_tasks])
    result = f"Отчёт #{report_id}\n\n" \
             f"{hlink(f'{surname} {first_name}', f'https://t.me/{username}')} — Black\n\n" \
             f"<b>Дата:</b> {today_str}\n\n" \
             f"<b>Заработал:</b> - {earned} руб.\n\n" \
             f"✅<b>Выполнено</b>\n\n" \
             f"{done_tasks}\n\n" \
             f"❌<b>Не выполнено</b>\n\n" \
             f"{not_done_tasks}\n\n" \
             f"📝<b>План на</b> - {tomorrow}\n\n" \
             f"{scheduled_tasks}"
    return result


async def update_report_data(report_id: int):
    curr_report = await sqlite_db.get_report_by_id(report_id)

    member = await sqlite_db.get_user_by_id(curr_report[1])

    surname = member[5]
    first_name = member[4]
    username = member[3]
    phone_time = curr_report[2]
    done_tasks = curr_report[3].split('\n')
    not_done_tasks = curr_report[4].split('\n')
    scheduled_tasks = curr_report[5].split('\n')
    message_id = curr_report[6]

    new_output = await print_report(report_id, surname, first_name, username, phone_time,
                                    done_tasks, not_done_tasks, scheduled_tasks)

    await bot.edit_message_text(text=new_output, chat_id=CONFIG['report_channel'], message_id=message_id)


async def update_report_tracker():
    reports_count_data = {}
    members = await sqlite_db.get_users()
    for member in members:
        user_id = member[0]
        reports_count = await sqlite_db.count_user_reports(user_id)
        reports_count[f'{user_id}'] = reports_count
    with open('../data/rating_data.json', 'w', encoding='utf-8') as json_file:
        json.dump(reports_count_data, json_file, ensure_ascii=False, indent=4)


async def check_report_tracker():
    old_reports_count_data = get_json_file_contents('data/rating_data.json')
    reports_count_data = {}
    members = await sqlite_db.get_users()
    for member in members:
        user_id = member[0]
        reports_count = await sqlite_db.count_user_reports(user_id)
        reports_count[f'{user_id}'] = reports_count_data
    for key, value in old_reports_count_data:
        if key in reports_count_data and key in old_reports_count_data:
            user_id = int(key)
            user_rate = await sqlite_db.get_user_points(user_id)
            if value > old_reports_count_data[key]:
                user_rate += 1
            else:
                user_rate -= 1
            await sqlite_db.update_user_points(user_id, user_rate)
