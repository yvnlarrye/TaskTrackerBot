from aiogram import executor
from dispatcher import dp
from handlers import general, member, admin
import aioschedule
import asyncio

from utils.period_reports import *


async def on_startup(_):
    print('Bot has been successfully started.')
    await sqlite_db.db_connect()
    print('Connected to database')
    asyncio.create_task(scheduler())


async def scheduler():
    aioschedule.every().day.at("23:59").do(send_daily_report)
    aioschedule.every().wednesday.at("23:59").do(send_weekly_report)
    aioschedule.every().day.at("23:57").do(send_monthly_report)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


if __name__ == '__main__':
    executor.start_polling(dispatcher=dp,
                           on_startup=on_startup,
                           skip_updates=True)
