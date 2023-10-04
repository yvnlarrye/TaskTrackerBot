import re
from datetime import date
from aiogram import types


async def validate_date(parsed_date: str, message: types.Message):
    date_list = parsed_date.split('.')
    current_date = date.today()
    curr_dt_str = current_date.strftime("%d-%m-%y").split('-')
    if len(parsed_date) != 8:
        raise AttributeError
    if not (1 <= int(date_list[0]) <= 31):
        raise AttributeError
    if not (1 <= int(date_list[1]) <= 12):
        raise AttributeError
    if int(date_list[2]) < int(curr_dt_str[2]):
        raise AttributeError
    inpt_date = date(
        int('20' + date_list[2]),
        int(date_list[1]),
        int(date_list[0])
    )
    if inpt_date < current_date:
        await message.answer(text='Введенная дата не может быть меньше текущей!')
        raise AttributeError


async def validate_time(parsed_time: str):
    hh_mm = parsed_time.split(':')
    if len(parsed_time) != 5:
        raise AttributeError
    if not (0 <= int(hh_mm[0]) <= 23):
        raise AttributeError
    if not (0 <= int(hh_mm[1]) <= 59):
        raise AttributeError


def parse_time(string):
    pattern = r'(\d{2})[:\-](\d{2})'
    match = re.search(pattern, string)
    if match:
        hours = match.group(1)
        minutes = match.group(2)
        return f"{hours}:{minutes}"
    else:
        raise AttributeError
