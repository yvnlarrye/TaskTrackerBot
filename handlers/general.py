from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.exceptions import ChatNotFound
from aiogram.utils.markdown import hlink
from data.config import PASS
from dispatcher import dp
from keyboards.keyboards import permission_denied_message
from states import SessionRole
from utils.utils import is_admin, get_status_icon
from handlers.admin import admin_start
from handlers.member import member_start
from data import sqlite_db
from keyboards import keyboards as kb
from utils.utils import delete_prev_message, get_user_earned_total_amount
from dispatcher import bot
from data.config import CONFIG


async def is_user_joined_all_chats(user_id: int):
    for chat_id in CONFIG['channels'].values():
        user_channel_status = await bot.get_chat_member(user_id=user_id, chat_id=chat_id)
        if user_channel_status['status'] == 'left':
            return False
    return True


async def send_permission_denied_message(msg: Message):
    await msg.answer(permission_denied_message, reply_markup=kb.check_subscribes_kb)


@dp.message_handler(text='Проверить подписки', state='*')
async def check_subscribes(msg: Message, state: FSMContext):
    if await is_user_joined_all_chats(msg.from_id):
        await start(msg, state)
    else:
        await send_permission_denied_message(msg)
    await msg.delete()


@dp.message_handler(commands=['start'], state='*')
async def start(msg: Message, state: FSMContext):
    await state.reset_state()
    try:
        if await is_user_joined_all_chats(msg.from_id):
            if await sqlite_db.user_exists(msg.from_id):
                if await is_admin(msg.from_id):
                    keyboard = kb.intro_admin_kb
                else:
                    keyboard = kb.intro_member_kb
                m = await msg.answer('Выбери, за кого зайти:',
                                     reply_markup=keyboard)
                await state.update_data(msg=m)
            else:
                await msg.answer('🚫 У вас нет доступа к боту. Свяжитесь с администратором.')
        else:
            await send_permission_denied_message(msg)
    except ChatNotFound:
        await bot.send_message(chat_id=msg.from_id,
                               text='Для корректной работы добавьте бота во все подключенные чаты.')
    await msg.delete()


@dp.message_handler(commands=['logout'], state='*')
async def logout(msg: Message, state: FSMContext):
    if await is_user_joined_all_chats(msg.from_id):
        if await is_admin(msg.from_id):
            user_id = await sqlite_db.get_user_id(msg.from_id)
            await sqlite_db.update_user_role(user_id, 0)
            await msg.answer('Вы больше не администратор')
            await start(msg, state)
        else:
            await msg.answer('Команда доступна только администраторам.')
    else:
        await send_permission_denied_message(msg)


@dp.message_handler(commands=['admin'], state='*')
async def admin(msg: Message, state: FSMContext):
    if await is_user_joined_all_chats(msg.from_id):
        parts = msg.text.split()
        if len(parts) == 2:
            if parts[1] == PASS:
                if await sqlite_db.user_exists(msg.from_id):
                    user_id = await sqlite_db.get_user_id(msg.from_id)
                    await sqlite_db.update_user_role(user_id, 1)
                    await msg.answer('Новый администратор добавлен')
                    await start(msg, state)
    else:
        await send_permission_denied_message(msg)


@dp.message_handler(text='👨‍💻 Участник')
async def login_as_member(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    if await is_user_joined_all_chats(msg.from_id):
        if await sqlite_db.user_exists(msg.from_id):
            await member_start(msg, state)
    else:
        await send_permission_denied_message(msg)
    await msg.delete()


@dp.message_handler(text='🏴‍☠️ Админ')
async def login_as_admin(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    if await is_user_joined_all_chats(msg.from_id):
        if await sqlite_db.user_exists(msg.from_id):
            if await is_admin(msg.from_id):
                await admin_start(msg, state)
            else:
                await msg.answer('🚫 У вас нет прав администратора.')
        else:
            await msg.answer('🚫 У вас нет доступа к боту. Свяжитесь с администратором.')
    else:
        await send_permission_denied_message(msg)
    await msg.delete()


@dp.message_handler(text='🏠 Выйти', state='*')
async def back_to_main_menu(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    if await is_user_joined_all_chats(msg.from_id):
        await start(msg, state)
    else:
        await send_permission_denied_message(msg)


@dp.message_handler(text='🏆📈 Топы', state='*')
async def week_rating(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    if await is_user_joined_all_chats(msg.from_id):
        users = reversed(await sqlite_db.get_users_sorted_by_points())
        result_list = []
        for user in users:
            user_id = user[0]
            surname = user[5]
            first_name = user[4]
            user_name = user[3]
            user_status = user[7]
            user_points = user[6]
            result_list.append(
                f"{get_status_icon(user_status)}"
                f"{hlink(f'{first_name} {surname}', f'https://t.me/{user_name}')} — "
                f"🎯{user_points} / 💰 {await get_user_earned_total_amount(user_id)}"
            )
        result = '\n'.join(result_list)
        await msg.answer('<b>Имя — Баллы:</b>\n' + result,
                         reply_markup=kb.prev_step_reply_kb)
        await SessionRole.general.set()
    else:
        await send_permission_denied_message(msg)


@dp.message_handler(text='↩️ Вернуться назад', state=SessionRole.general)
async def back_to_admin_menu(msg: Message, state: FSMContext):
    if await is_user_joined_all_chats(msg.from_id):
        await start(msg, state)
    else:
        await send_permission_denied_message(msg)
