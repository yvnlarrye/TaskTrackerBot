import asyncio

from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.exceptions import MessageNotModified
from data import sqlite_db
from data.config import REQUEST_STATUS, CONFIG
from keyboards import keyboards as kb
from utils.utils import format_addressers, format_recipients, get_status_icon
from dispatcher import bot
from aiogram.utils.markdown import hlink


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

    prev_step_indices = to_members_indices.copy()

    if member_index in to_members_indices:
        to_members_indices.remove(member_index)
    elif len(to_members_indices) < 2:
        to_members_indices.append(member_index)

    await state.update_data(request_to=to_members_indices)
    if len(to_members_indices):
        if len(to_members_indices) == 1:
            await state.update_data(main_recipient=to_members_indices[0],
                                    secondary_recipient=None)
        elif len(to_members_indices) == 2:
            await state.update_data(main_recipient=to_members_indices[0],
                                    secondary_recipient=to_members_indices[1])
    curr_users = data['curr_users']
    new_keyboard = await kb.update_recipients_kb(curr_users, to_members_indices)

    if prev_step_indices != to_members_indices:
        formatted_users = await format_recipients(curr_users, users_indices=to_members_indices)
        await bot.edit_message_text(chat_id=cb.message.chat.id,
                                    message_id=cb.message.message_id,
                                    text=formatted_users,
                                    reply_markup=new_keyboard)
    else:
        m = await cb.message.answer('Можно добавить одного основного и одного дополнительного исполнителя.')
        await asyncio.sleep(2)
        await m.delete()


async def commit_request(data: dict):
    author_id = await sqlite_db.get_user_id(data['author_telegram_id'])

    users = data['curr_users']
    addressers = '\n'.join([users[user_index][3] for user_index in data['request_from']])
    main_recipient = users[data['main_recipient']][3]
    if data['secondary_recipient'] is not None:
        secondary_recipient = users[data['secondary_recipient']][3]
    else:
        secondary_recipient = ''
    text = data['text']
    date = data['date']

    await sqlite_db.add_request(author_id=author_id,
                                status=1,
                                addressers=addressers,
                                main_recipient=main_recipient,
                                secondary_recipient=secondary_recipient,
                                text=text,
                                date=date)


def print_request(request_id: int, status: int, addressers: list, main_recipient: tuple,
                  secondary_recipient: tuple, text: str, date: str, video_link=None, hashtag_indices: list = None):
    addr_output = '\n'.join([
        f"{get_status_icon(addresser[3])} {hlink(f'{addresser[1]} {addresser[2]}', f'https://t.me/{addresser[0]}')} — {addresser[3]}"
        for addresser in addressers
    ])
    main_recipient_output = f"{get_status_icon(main_recipient[3])} {hlink(f'{main_recipient[1]} {main_recipient[2]}', f'https://t.me/{main_recipient[0]}')} — {main_recipient[3]}"
    if len(secondary_recipient):
        secondary_recipient_output = \
            f"Дополнительный исполнитель:\n" \
            f"{get_status_icon(secondary_recipient[3])} " \
            f"{hlink(f'{secondary_recipient[1]} {secondary_recipient[2]}', f'https://t.me/{secondary_recipient[0]}')} — " \
            f"{secondary_recipient[3]}\n\n"
    else:
        secondary_recipient_output = ''

    video_link_output = ''
    if video_link:
        video_link_output = '\n\n' + hlink('Запись с Zoom', video_link)

    hashtags_output = ''
    if hashtag_indices:
        hashtags = CONFIG['hashtags']
        hashtags_output = '\n\n<b>Теги:</b>\n' + ' '.join([hashtags[i]['name'] for i in hashtag_indices])

    result = f"Запрос #{request_id}\n\n" \
             f"<b>Статус:</b>\n" \
             f"{status}\n" \
             f"\n" \
             f"<b>От кого:</b>\n" \
             f"{addr_output}\n" \
             f"\n" \
             f"<b>Кому:</b>\n" \
             f"\n" \
             f"Основной исполнитель:\n" \
             f"{main_recipient_output}\n\n" \
             f"{secondary_recipient_output}" \
             f"<b>Запрос:</b>\n" \
             f"{text}\n" \
             f"\n" \
             f"<b>Срок:</b> {date}" \
             f"{video_link_output}" \
             f"{hashtags_output}"
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


async def update_request_message(request_id, video_link=None, hashtag_indices: list = None):
    curr_request = await sqlite_db.get_request_by_id(request_id)
    req_status = request_status_str(curr_request[2])
    addressers = curr_request[3].split('\n')
    main_recipient = curr_request[4].strip()
    secondary_recipient = curr_request[5].strip()

    addressers_transfer_data = []
    for username in addressers:
        addresser = await sqlite_db.get_user_by_username(username.strip())
        addressers_transfer_data.append(
            (addresser[3], addresser[4], addresser[5], addresser[7],)
        )

    main_recipient = await sqlite_db.get_user_by_username(main_recipient)
    main_recipient_transfer_data = (main_recipient[3], main_recipient[4], main_recipient[5], main_recipient[7],)

    if secondary_recipient != '':
        secondary_recipient = await sqlite_db.get_user_by_username(secondary_recipient)
        secondary_recipient_transfer_data = (
            secondary_recipient[3], secondary_recipient[4], secondary_recipient[5], secondary_recipient[7],
        )
    else:
        secondary_recipient_transfer_data = ()

    text = curr_request[6]
    date = curr_request[7]
    message_id = curr_request[8]
    new_output = print_request(request_id, req_status, addressers_transfer_data, main_recipient_transfer_data,
                               secondary_recipient_transfer_data, text, date, video_link, hashtag_indices)
    try:
        await bot.edit_message_text(text=new_output, chat_id=CONFIG['channels']['request_channel'], message_id=message_id)
    except MessageNotModified:
        pass

    if hashtag_indices is not None:
        hashtags = CONFIG['hashtags']
        for i in hashtag_indices:
            curr_tag_thread_id = hashtags[i]['thread_id']
            await bot.send_message(chat_id=CONFIG['channels']['knowledge_base'],
                                   text=new_output,
                                   reply_to_message_id=curr_tag_thread_id)


async def update_req_recipients_points(req, update_mode: str):
    sign = None
    if update_mode == '+':
        sign = 1
    elif update_mode == '-':
        sign = -1

    if sign is not None:
        main_recipient_id = (await sqlite_db.get_user_by_username(req[4]))[0]
        main_recipient_rate = await sqlite_db.get_user_points(main_recipient_id)
        main_recipient_rate += 1 * sign
        await sqlite_db.add_points_to_user(main_recipient_id, 1 * sign)
        await sqlite_db.update_user_points(main_recipient_id, main_recipient_rate)

        secondary_recipient = req[5]
        if secondary_recipient != '':
            secondary_recipient_id = (await sqlite_db.get_user_by_username(req[5]))[0]
            recipient_rate = await sqlite_db.get_user_points(secondary_recipient_id)
            recipient_rate += 0.5 * sign
            await sqlite_db.add_points_to_user(secondary_recipient_id, 0.5 * sign)
            await sqlite_db.update_user_points(secondary_recipient_id, recipient_rate)


async def update_request_hashtags(cb: CallbackQuery, state: FSMContext):
    user_index = int(cb.data[5:])

    data = await state.get_data()
    if 'hashtag_indices' not in data:
        await state.update_data(hashtag_indices=[])

    data = await state.get_data()
    hashtag_indices = data['hashtag_indices']

    if user_index in hashtag_indices:
        hashtag_indices.remove(user_index)
    else:
        hashtag_indices.append(user_index)
    await state.update_data(hashtag_indices=hashtag_indices)
    new_keyboard = kb.hashtag_kb(hashtag_indices)

    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=data['message_text'],
                                reply_markup=new_keyboard)
