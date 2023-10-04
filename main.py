from aiogram import executor
from dispatcher import dp
from handlers import general, member, admin
from data import sqlite_db
import aioschedule
import asyncio
# from handlers.general import update_report_tracker, check_report_tracker


async def on_startup(_):
    print('Bot has been successfully started.')
    await sqlite_db.db_connect()
    print('Connected to database')
    # asyncio.create_task(scheduler())


async def scheduler():
    # aioschedule.every().day.at("19:59").do(update_report_tracker)
    # aioschedule.every().day.at("22:01").do(check_report_tracker)
    # aioschedule.every().week.do(reset_raring)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


if __name__ == '__main__':
    executor.start_polling(dispatcher=dp,
                           on_startup=on_startup,
                           skip_updates=True)
