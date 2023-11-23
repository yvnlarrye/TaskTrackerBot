import asyncio
from aiogram import executor
from aiogram.utils.exceptions import TelegramAPIError
from google.google_manager import init_google_service
from dispatcher import dp
from handlers import general, member, admin

from utils.tasks import scheduler
from data import sqlite_db


async def on_startup(_):
    print('Bot has been successfully started.')
    await sqlite_db.db_connect()
    print('Connected to database')
    init_google_service()
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    try:
        executor.start_polling(dispatcher=dp,
                               on_startup=on_startup,
                               skip_updates=True)
    except TelegramAPIError as e:
        print(e)
        pass
