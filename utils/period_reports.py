from datetime import timedelta

from aiogram.utils.exceptions import ChatNotFound, BotBlocked
from aiogram.utils.markdown import hlink

from data import sqlite_db
from data.config import CONFIG
from dispatcher import bot
from utils.utils import get_status_icon, curr_datetime


async def send_daily_report():
    users = await sqlite_db.get_users()
    for user in users:
        telegram_id = user[1]
        if telegram_id not in CONFIG['hidden_users']:
            check_amount_records = await sqlite_db.get_user_check_amounts_per_day(user[0])
            user_output = f"{get_status_icon(user[7])} {hlink(f'{user[4]} {user[5]}', f'https://t.me/{user[3]}')} — {user[7]}"

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

            report_output = f"<b>Дата:</b> {curr_datetime().strftime('%d.%m.%y')}\n\n" \
                            f"{user_output}\n\n" \
                            f"💸 Заработал: {total_earned}\n" \
                            f"✅ Заработал баллов: {total_points}\n" \
                            f"🎯 Закрыл целей: {goals_count}\n" \
                            f"💰 Целей закрыто на сумму: {total_check_amount}"

            await bot.send_message(chat_id=CONFIG['channels']['period_reports'],
                                   reply_to_message_id=CONFIG['period_reports']['daily']['thread_id'],
                                   text=report_output)


async def send_weekly_report():
    users = await sqlite_db.get_users()
    for user in users:
        telegram_id = user[1]
        if telegram_id not in CONFIG['hidden_users']:
            check_amount_records = await sqlite_db.get_user_check_amounts_per_week(user[0])
            user_output = f"{get_status_icon(user[7])} {hlink(f'{user[4]} {user[5]}', f'https://t.me/{user[3]}')} — {user[7]}"

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

            report_output = f"<b>Даты:</b> {(curr_datetime() - timedelta(days=6)).strftime('%d.%m.%y')} - {curr_datetime().strftime('%d.%m.%y')}\n\n" \
                            f"{user_output}\n\n" \
                            f"💸 Заработал: {total_earned}\n" \
                            f"✅ Заработал баллов: {total_points}\n" \
                            f"🎯 Закрыл целей: {goals_count}\n" \
                            f"💰 Целей закрыто на сумму: {total_check_amount}"

            await bot.send_message(chat_id=CONFIG['channels']['period_reports'],
                                   reply_to_message_id=CONFIG['period_reports']['weekly']['thread_id'],
                                   text=report_output)


async def send_monthly_report():
    if (curr_datetime() + timedelta(days=1)).month != curr_datetime().month:
        users = await sqlite_db.get_users()
        for user in users:
            telegram_id = user[1]
            if telegram_id not in CONFIG['hidden_users']:
                check_amount_records = await sqlite_db.get_user_check_amounts_per_month(user[0])
                user_output = f"{get_status_icon(user[7])} {hlink(f'{user[4]} {user[5]}', f'https://t.me/{user[3]}')} — {user[7]}"

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

                report_output = f"<b>Месяц:</b> {curr_datetime().strftime('%B, %Y')}\n\n" \
                                f"{user_output}\n\n" \
                                f"💸 Заработал: {total_earned}\n" \
                                f"✅ Заработал баллов: {total_points}\n" \
                                f"🎯 Закрыл целей: {goals_count}\n" \
                                f"💰 Целей закрыто на сумму: {total_check_amount}"

                await bot.send_message(chat_id=CONFIG['channels']['period_reports'],
                                       reply_to_message_id=CONFIG['period_reports']['monthly']['thread_id'],
                                       text=report_output)


async def first_reminder():
    users = await sqlite_db.get_users()
    for user in users:
        try:
            await bot.send_message(chat_id=user[1], text='Привет! У тебя есть 2 часа, чтобы заполнить ежедневную отчётность и заработать 1 балл!')
        except ChatNotFound:
            await sqlite_db.remove_user_by_id(user[0])
        except BotBlocked:
            pass


async def second_reminder():
    users = await sqlite_db.get_users()
    for user in users:
        user_id = user[0]
        user_reports_count = await sqlite_db.count_user_reports_per_day(user_id)
        if not user_reports_count:
            try:
                await bot.send_message(chat_id=user[1], text='Ты ещё успеваешь написать свои денежные задачи⏳💰')
            except ChatNotFound:
                await sqlite_db.remove_user_by_id(user_id)
            except BotBlocked:
                pass



