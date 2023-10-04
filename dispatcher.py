from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
import os
from dotenv import load_dotenv

load_dotenv('.env')
storage = MemoryStorage()
BOT_TOKEN = str(os.getenv('TOKEN_API'))
bot = Bot(token=BOT_TOKEN,
          parse_mode=ParseMode.HTML,
          disable_web_page_preview=True)

dp = Dispatcher(bot=bot, storage=storage)
