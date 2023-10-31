from datetime import timedelta, time, datetime

import aioschedule
import asyncio
from aiogram.utils.exceptions import ChatNotFound, BotBlocked, CantInitiateConversation
from aiogram.utils.markdown import hlink

from data import sqlite_db
from data.config import CONFIG
from dispatcher import bot
from utils.utils import get_status_icon, curr_datetime, is_user_recipient
from calendar import monthrange


async def send_daily_report():
    users = await sqlite_db.get_users()
    result = [f"<b>Дата:</b> {curr_datetime().strftime('%d.%m.%y')}"]
    for user in users:
        telegram_id = user[1]
        if telegram_id not in CONFIG['hidden_users']:
            check_amount_records = await sqlite_db.get_user_check_amounts_per_day(user[0])
            user_output = f"{hlink(f'{user[4]} {user[5]}', f'tg://user?id={user[1]}')} — {get_status_icon(user[7])} {user[7]}"

            goals_count = len(check_amount_records)

            total_check_amount = 0
            for check in check_amount_records:
                total_check_amount += check[0]

            total_earned = 0
            earned_records = await sqlite_db.get_user_earned_per_day(user[0])
            for earned in earned_records:
                total_earned += earned[0]

            points_records = await sqlite_db.get_user_points_per_day(user[0])
            total_points = 0
            for points_record in points_records:
                total_points += points_record[0]

            requests = await sqlite_db.get_all_requests()
            reqs_to_me_count = 0
            reqs_from_me_count = 0
            for req in requests:
                if is_user_recipient(req, user) and req[2] == 1:
                    reqs_to_me_count += 1
                if req[2] == 1 and user[0] == req[1]:
                    reqs_from_me_count += 1

            report_output = f"{user_output}\n" \
                            f"💸{total_earned} / 💯{total_points} / 🎯{goals_count} на {total_check_amount}₽\n" \
                            f"Незакрытые запросы тебе/твои: {reqs_to_me_count} / {reqs_from_me_count}"

            result.append(report_output)
    if len(users):
        await bot.send_message(chat_id=CONFIG['channels']['period_reports'],
                               reply_to_message_id=CONFIG['period_reports']['daily']['thread_id'],
                               text='\n\n'.join(result))


async def send_weekly_report():
    users = await sqlite_db.get_users()
    result = [
        f"<b>Даты:</b> {(curr_datetime() - timedelta(days=6)).strftime('%d.%m.%y')} - {curr_datetime().strftime('%d.%m.%y')}"]
    for user in users:
        telegram_id = user[1]
        if telegram_id not in CONFIG['hidden_users']:
            check_amount_records = await sqlite_db.get_user_check_amounts_per_week(user[0])
            user_output = f"{hlink(f'{user[4]} {user[5]}', f'tg://user?id={user[1]}')} — {get_status_icon(user[7])} {user[7]}"

            goals_count = len(check_amount_records)

            total_check_amount = 0
            for check in check_amount_records:
                total_check_amount += check[0]

            total_earned = 0
            earned_records = await sqlite_db.get_user_earned_per_week(user[0])
            for earned in earned_records:
                total_earned += earned[0]

            points_records = await sqlite_db.get_user_points_per_week(user[0])
            total_points = 0
            for points_record in points_records:
                total_points += points_record[0]

            requests = await sqlite_db.get_all_requests()
            reqs_to_me_count = 0
            reqs_from_me_count = 0
            for req in requests:
                if is_user_recipient(req, user) and req[2] == 1:
                    reqs_to_me_count += 1
                if req[2] == 1 and user[0] == req[1]:
                    reqs_from_me_count += 1

            report_output = f"{user_output}\n" \
                            f"💸{total_earned} / 💯{total_points} / 🎯{goals_count} на {total_check_amount}₽\n" \
                            f"Незакрытые запросы тебе/твои: {reqs_to_me_count} / {reqs_from_me_count}"

            result.append(report_output)
    if len(users):
        await bot.send_message(chat_id=CONFIG['channels']['period_reports'],
                               reply_to_message_id=CONFIG['period_reports']['weekly']['thread_id'],
                               text='\n\n'.join(result))


async def send_monthly_report():
    if (curr_datetime() + timedelta(days=1)).month != curr_datetime().month:
        users = await sqlite_db.get_users()
        for user in users:
            telegram_id = user[1]
            if telegram_id not in CONFIG['hidden_users']:
                check_amount_records = await sqlite_db.get_user_check_amounts_per_month(user[0])
                user_output = f"{hlink(f'{user[4]} {user[5]}', f'tg://user?id={user[1]}')} — {get_status_icon(user[7])} {user[7]}"

                goals_count = len(check_amount_records)

                total_check_amount = 0
                for check in check_amount_records:
                    total_check_amount += check[0]

                total_earned = 0
                earned_records = await sqlite_db.get_user_earned_per_month(user[0])
                for earned in earned_records:
                    total_earned += earned[0]

                points_records = await sqlite_db.get_user_points_per_month(user[0])
                total_points = 0
                for points_record in points_records:
                    total_points += points_record[0]

                created_requests_count = await sqlite_db.count_user_requests_per_month(user[0])

                done_requests_count = 0
                requests = await sqlite_db.get_all_requests()
                for req in requests:
                    if is_user_recipient(user, req) and req[2] == 2:
                        done_requests_count += 1

                reports_count = await sqlite_db.count_user_reports(user[0])

                current_year = datetime.now().year
                current_month = datetime.now().month
                days = monthrange(current_year, current_month)[1]

                report_output = f"<b>Месяц:</b> {curr_datetime().strftime('%B, %Y')}\n\n" \ 
                                f"{user_output}\n\n" \
                                f"💸 Заработал: {total_earned}\n" \
                                f"✅ Заработал баллов: {total_points}\n" \
                                f"🎯 Закрыл целей: {goals_count}\n" \
                                f"💰 Целей закрыто на сумму: {total_check_amount}\n" \
                                f"📝 Создано запросов: {created_requests_count}\n" \
                                f"📝 Решено запросов: {done_requests_count}\n" \
                                f"📩 Заполнено отчётов: {reports_count}\n" \
                                f"📩 Пропущено отчётов: {days - reports_count}"

                await bot.send_message(chat_id=CONFIG['channels']['period_reports'],
                                       reply_to_message_id=CONFIG['period_reports']['monthly']['thread_id'],
                                       text=report_output)


async def first_remind():
    users = await sqlite_db.get_users()
    for user in users:
        try:
            await bot.send_message(chat_id=user[1],
                                   text='Привет! У тебя есть 2 часа, чтобы заполнить ежедневную отчётность и заработать 1 балл!')
        except ChatNotFound:
            await sqlite_db.remove_user_by_id(user[0])
        except (BotBlocked, CantInitiateConversation):
            pass


async def second_remind():
    users = await sqlite_db.get_users()
    for user in users:
        user_id = user[0]
        user_reports_count = await sqlite_db.count_user_reports_per_day(user_id)
        if not user_reports_count:
            try:
                await bot.send_message(chat_id=user[1], text='Ты ещё успеваешь написать свои денежные задачи⏳💰')
            except ChatNotFound:
                await sqlite_db.remove_user_by_id(user_id)
            except (BotBlocked, CantInitiateConversation):
                pass


async def report_track():
    users = await sqlite_db.get_users()
    for user in users:
        user_id = user[0]
        user_reports_count = await sqlite_db.count_user_reports_per_day(user_id)

        points_amount = 1 if user_reports_count else -1
        user_points = await sqlite_db.get_user_points(user_id)
        user_points += points_amount
        await sqlite_db.add_points_to_user(user_id, points_amount)

        await sqlite_db.update_user_points(user_id, user_points)


async def tasks_clean():
    tasks = await sqlite_db.get_tasks_ids_scheduled_on_today()
    for task in tasks:
        await sqlite_db.remove_scheduled_task_by_id(task[0])


async def scheduler():
    aioschedule.every().day.at("23:59").do(send_daily_report)
    aioschedule.every().sunday.at("23:59").do(send_weekly_report)
    aioschedule.every().day.at("23:58").do(send_monthly_report)

    report_time = CONFIG['report_time']

    mid_notif_time = time(hour=int(report_time['start'].split(":")[0]) + 1,
                          minute=int(report_time['start'].split(":")[1]) + 30).strftime("%H:%M")

    aioschedule.every().day.at(report_time['start']).do(first_remind)
    aioschedule.every().day.at(mid_notif_time).do(second_remind)

    aioschedule.every().day.at(report_time['end']).do(report_track)

    clean_tasks_time = time(hour=int(report_time['end'].split(":")[0]),
                            minute=int(report_time['end'].split(":")[1]) + 1).strftime("%H:%M")

    aioschedule.every().day.at(clean_tasks_time).do(tasks_clean)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)
