from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from data.config import PASS, STATUS
from dispatcher import dp
from states import SessionRole, UserEdition
from utils.utils import is_admin
from handlers.admin import admin_start
from handlers.member import member_start
from data import sqlite_db
from keyboards import keyboards as kb
from utils.utils import delete_prev_message


@dp.message_handler(commands=['start'], state='*')
async def start(msg: Message, state: FSMContext):
    await state.finish()
    if await sqlite_db.user_exists(msg.from_id):
        if await is_admin(msg.from_id):
            keyboard = kb.intro_admin_kb
        else:
            keyboard = kb.intro_member_kb
        m = await msg.answer('Выбери, за кого зайти:',
                             reply_markup=keyboard)
        await state.update_data(msg=m)
    else:
        await msg.answer('🚫 У вас нет доступа к данному сервису. Свяжитесь с администратором сервиса.')
    await msg.delete()


@dp.message_handler(commands=['logout'], state='*')
async def logout(msg: Message, state: FSMContext):
    if await is_admin(msg.from_id):
        user_id = await sqlite_db.get_user_id(msg.from_id)
        await sqlite_db.update_user_role(user_id, 0)
        await msg.answer('Вы больше не администратор')
        await start(msg, state)
    else:
        await msg.answer('Команда доступна только администраторам.')


@dp.message_handler(commands=['admin'], state='*')
async def admin(msg: Message, state: FSMContext):
    parts = msg.text.split()
    if len(parts) == 2:
        if parts[1] == PASS:
            if await sqlite_db.user_exists(msg.from_id):
                user_id = await sqlite_db.get_user_id(msg.from_id)
                await sqlite_db.update_user_role(user_id, 1)
                await msg.answer('Новый администратор добавлен')
                await start(msg, state)
            else:
                await msg.answer('Отправьте ваше имя и фамилию:\n'
                                 'Например: Иван Иванов')
                await UserEdition.new_admin_name.set()


@dp.message_handler(text='👨‍💻 Участник')
async def login_as_member(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    if await sqlite_db.user_exists(msg.from_id):
        await member_start(msg, state)
    else:
        await msg.answer('🚫 У вас нет доступа к данному сервису. Свяжитесь с администратором сервиса.')
    await msg.delete()


@dp.message_handler(text='☠️ Админ')
async def login_as_admin(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    if await sqlite_db.user_exists(msg.from_id):
        if await is_admin(msg.from_id):
            await admin_start(msg, state)
        else:
            await msg.answer('🚫 У вас нет прав администратора.')
    else:
        await msg.answer('🚫 У вас нет доступа к данному сервису. Свяжитесь с администратором сервиса.')
    await msg.delete()


@dp.message_handler(text='🏠 Выйти', state='*')
async def back_to_main_menu(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    await start(msg, state)


@dp.message_handler(text='🏆📈 Топы', state='*')
async def week_rating(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    members = reversed(await sqlite_db.get_users_sorted_by_points())
    result_list = []
    for member in members:
        result_list.append(f"{STATUS[str(member[7]).lower()]['icon']} {member[5]} {member[4]} @{member[3]} — 🎯{member[6]}")
    result = '\n'.join(result_list)
    await msg.answer('<b>Имя — Баллы:</b>\n' + result,
                     reply_markup=kb.prev_step_reply_kb)
    await SessionRole.general.set()


@dp.message_handler(text='↩️ Вернуться назад', state=SessionRole.general)
async def back_to_admin_menu(msg: Message, state: FSMContext):
    await start(msg, state)
