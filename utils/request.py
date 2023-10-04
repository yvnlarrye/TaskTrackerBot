import re

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State
from aiogram.types import CallbackQuery, Message

from data import sqlite_db
from data.config import REQUEST_STATUS, CONFIG
from keyboards import keyboards as kb
from states import SessionRole
from utils.utils import format_addressers, format_recipients
from dispatcher import bot
from utils.validators import validate_date, parse_time, validate_time
from datetime import datetime


async def request_from_user(cb: CallbackQuery, state: FSMContext):
    member_index = int(cb.data[5:])

    data = await state.get_data()
    if 'request_from' not in data:
        await state.update_data(request_from=[])

    data = await state.get_data()
    from_members_indices = data['request_from']

    if member_index in from_members_indices:
        from_members_indices.remove(member_index)
    else:
        from_members_indices.append(member_index)
    await state.update_data(request_from=from_members_indices)
    curr_users = data['curr_users']
    new_keyboard = await kb.update_addressers_kb(curr_users, from_members_indices)

    formatted_users = await format_addressers(curr_users, users_indices=from_members_indices)
    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=formatted_users,
                                reply_markup=new_keyboard)


async def request_to_user(cb: CallbackQuery, state: FSMContext):
    member_index = int(cb.data[5:])

    data = await state.get_data()
    if 'request_to' not in data:
        await state.update_data(request_to=[])

    data = await state.get_data()
    to_members_indices = data['request_to']

    if member_index in to_members_indices:
        to_members_indices.remove(member_index)
    else:
        to_members_indices.append(member_index)

    await state.update_data(request_to=to_members_indices)
    if len(to_members_indices):
        if len(to_members_indices) == 1:
            await state.update_data(main_recipient=to_members_indices[0],
                                    secondary_recipients=[])
        elif len(to_members_indices) > 1:
            await state.update_data(main_recipient=to_members_indices[0],
                                    secondary_recipients=to_members_indices[1:])
    curr_users = data['curr_users']
    new_keyboard = await kb.update_recipients_kb(curr_users, to_members_indices)

    formatted_users = await format_recipients(curr_users, users_indices=to_members_indices)
    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=formatted_users,
                                reply_markup=new_keyboard)


async def commit_request(data: dict):
    author_id = await sqlite_db.get_user_id(data['author_telegram_id'])

    users = data['curr_users']
    addressers = '\n'.join([users[user_index][3] for user_index in data['request_from']])
    main_recipient = users[data['main_recipient']][3]

    if 'secondary_recipients' in data:
        secondary_recipients = '\n'.join([users[user_index][3] for user_index in data['secondary_recipients']])
    else:
        secondary_recipients = ''
    text = data['text']
    date_time = f"{data.get('date')} {data.get('time')}"

    await sqlite_db.add_request(author_id=author_id,
                                status=1,
                                addressers=addressers,
                                main_recipient=main_recipient,
                                secondary_recipients=secondary_recipients,
                                text=text,
                                datetime=date_time)


async def request_date(msg: Message, state: FSMContext, current_state: State):
    try:
        result = re.sub(r"[/\\-]", ".", re.search(r"(\d+.*?\d+.*?\d+)", msg.text).group(1))
        await validate_date(result, msg)
        await state.update_data(date=result)
        await current_state.set()
        await msg.answer(f'Введите время:\n'
                         f'Например: {datetime.now().strftime("%H:%M")}',
                         reply_markup=kb.prev_step_reply_kb)
    except AttributeError:
        date = datetime.now().strftime('%d.%m.%y')
        await msg.answer(text='Неверный формат даты',
                         reply_markup=kb.prev_step_reply_kb)
        await msg.answer(f'Введите дату срока запроса в формате:\n'
                         f'DD.MM.YY\n'
                         f'Например: {date}')


async def request_time(msg: Message, state: FSMContext):
    try:
        time = parse_time(msg.text)
        await validate_time(time)
        data = await state.get_data()
        date_time = f"{data['date']} {time}"
        requests = await sqlite_db.get_user_requests(data['user_id'])
        request_id = requests[data['req_index']][0]
        await sqlite_db.update_request_datetime(request_id, date_time)

        await update_request_message(request_id)

        await msg.answer('Срок успешно изменен.',
                         reply_markup=kb.member_menu_kb)
        await state.finish()
        await SessionRole.member.set()
    except AttributeError:
        await msg.answer(text='Неверный формат времени',
                         reply_markup=kb.prev_step_reply_kb)
        await msg.answer(f'Введите время:\n'
                         f'Например: {datetime.now().strftime("%H:%M")}')


def print_request(request_id: int, status: int, addressers: list, main_recipient: str,
                  secondary_recipients: list, text: str, date: str, time: str):
    result = f"Запрос #{request_id}\n\n" \
             f"<b>Статус:</b>\n" \
             f"{status}\n" \
             f"\n" \
             f"<b>От кого:</b>\n" \
             f"{', '.join(['@' + addresser for addresser in addressers])}\n" \
             f"\n" \
             f"<b>Кому:</b>\n" \
             f"\n" \
             f"Основной исполнитель:\n" \
             f"@{main_recipient}\n" \
             f"\n" \
             f"Дополнительные исполнители:\n" \
             f"{', '.join(['@' + recipient for recipient in secondary_recipients])}\n" \
             f"\n" \
             f"<b>Запрос:</b>\n" \
             f"{text}\n" \
             f"\n" \
             f"<b>Срок:</b>\n" \
             f"{date} - {time}"
    return result


def request_status_str(request_status: int):
    if request_status == 0:
        return REQUEST_STATUS['not_done']
    elif request_status == 1:
        return REQUEST_STATUS['in_progress']
    elif request_status == 2:
        return REQUEST_STATUS['done']
    else:
        raise AttributeError


async def update_request_message(request_id):
    curr_request = await sqlite_db.get_request_by_id(request_id)
    req_status = request_status_str(curr_request[2])
    addressers = curr_request[3].split('\n')
    main_recipient = curr_request[4]
    secondary_recipients = curr_request[5]
    if secondary_recipients == '':
        secondary_recipients = []
    else:
        secondary_recipients = curr_request[5].split('\n')
    text = curr_request[6]
    date_time = str(curr_request[7]).split()
    date = date_time[0]
    time = date_time[1]
    message_id = curr_request[8]
    new_output = print_request(request_id, req_status, addressers, main_recipient,
                               secondary_recipients, text, date, time)

    await bot.edit_message_text(text=new_output, chat_id=CONFIG['request_channel'], message_id=message_id)
