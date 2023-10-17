import json
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import (
    Message, CallbackQuery
)
from aiogram.utils.exceptions import MessageToEditNotFound, MessageIdInvalid

from dispatcher import dp, bot
from keyboards import keyboards as kb
from utils.reports import update_report_message
from utils.request import update_request_message

from utils.utils import is_admin, requestContainsUser
from data import sqlite_db
from states import SessionRole, UserEdition, Channel, Points, EditRequest
from data.config import CONFIG, STATUS
from utils.utils import delete_prev_message


async def admin_start(msg: Message, state: FSMContext):
    m = await msg.answer(text='Админ панель:',
                         reply_markup=kb.admin_menu_kb)
    await state.reset_data()
    await state.update_data(msg=m)
    await SessionRole.admin.set()


async def admin_reset(state: FSMContext):
    await state.reset_data()
    await SessionRole.admin.set()


@dp.message_handler(text='↩️ Вернуться назад', state=[SessionRole.admin,
                                                      UserEdition.admin,
                                                      UserEdition.member,
                                                      UserEdition.remove_member,
                                                      Points.add_amount,
                                                      Points.reduce_amount])
async def back_to_admin_menu(msg: Message, state: FSMContext):
    await admin_start(msg, state)


@dp.callback_query_handler(text='prev_step', state=[Points.add, Points.reduce, Channel.choose,
                                                    Channel.listening_request_channel,
                                                    Channel.listening_report_channel,
                                                    Channel.listening_goals_channel,
                                                    EditRequest.remove,
                                                    UserEdition.remove_member,
                                                    UserEdition.edit_status])
async def back_to_admin_menu_cb(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await admin_start(cb.message, state)


@dp.message_handler(text='✅ Добавить админа', state=SessionRole.admin)
async def add_admin(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    await msg.answer('Перешлите сюда сообщение от человека, которого хотите добавить как администратора:',
                     reply_markup=kb.prev_step_reply_kb)
    await UserEdition.admin.set()


@dp.message_handler(text='✅ Добавить участника', state=SessionRole.admin)
async def add_member(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    await msg.answer('Перешлите сюда сообщение от человека, которого хотите добавить как участника:',
                     reply_markup=kb.prev_step_reply_kb)
    await UserEdition.member.set()


@dp.message_handler(state=UserEdition.member)
async def member_name(msg: Message, state: FSMContext):
    try:
        user_id = msg.forward_from.id
        if await sqlite_db.user_exists(user_id):
            await msg.answer('Участник уже существует.',
                             reply_markup=kb.prev_step_reply_kb)
        else:
            username = msg.forward_from.username
            await state.update_data(username=username, user_id=user_id)
            await msg.answer('Введите имя участника:',
                             reply_markup=kb.prev_step_reply_kb)
            await UserEdition.member_first_name.set()
    except AttributeError:
        await msg.answer('Вы не переслали сообщение, или пользователь запретил перессылку',
                         reply_markup=kb.prev_step_reply_kb)
        await SessionRole.admin.set()


@dp.message_handler(state=UserEdition.member_first_name)
async def member_surname(msg: Message, state: FSMContext):
    await state.update_data(first_name=msg.text)
    await msg.answer('Введите фамилию участника:',
                     reply_markup=kb.prev_step_reply_kb)
    await UserEdition.member_surname.set()


@dp.message_handler(state=UserEdition.member_surname)
async def member_input(msg: Message, state: FSMContext):
    await state.update_data(surname=msg.text)
    data = await state.get_data()

    user_id = data['user_id']
    user_name = data['username']
    first_name = data['first_name']
    surname = data['surname']

    await sqlite_db.add_member(user_id, user_name, first_name, surname)
    await msg.answer(f'✅ Добавлен новый участник: {first_name} {surname} @{user_name}',
                     reply_markup=kb.admin_menu_kb)
    await admin_reset(state)


@dp.message_handler(state=UserEdition.admin)
async def admin_input(msg: Message, state: FSMContext):
    try:
        user_id = msg.forward_from.id
        if await sqlite_db.user_exists(user_id):
            if not await is_admin(user_id):
                await msg.answer('Участник уже существует. Назначить его администратором?',
                                 reply_markup=kb.approve_promotion_kb)
                await state.update_data(new_user_id=user_id)
                await UserEdition.ask_make_admin.set()
            else:
                await msg.answer('Такой администратор уже назначен.',
                                 reply_markup=kb.prev_step_reply_kb)
        else:
            # TODO
            # if user_name is not None:
            #     await add_admin(user_id, user_name if user_name is not None else '')
            # await msg.answer(f'✅ Добавлен новый администратор: @{user_name} ',
            #                  reply_markup=kb.prev_step_kb)
            await msg.answer('Такого участника еще нет',
                             reply_markup=kb.prev_step_reply_kb)
    except AttributeError:
        await msg.answer('Вы не переслали сообщение, или пользователь запретил перессылку',
                         reply_markup=kb.prev_step_reply_kb)
        await SessionRole.admin.set()


@dp.callback_query_handler(state=UserEdition.ask_make_admin)
async def promote_member(cb: CallbackQuery, state: FSMContext):
    if cb.data == 'approve_prom':
        data = await state.get_data()
        user_id = await sqlite_db.get_user_id(data['new_user_id'])
        await sqlite_db.update_user_role(user_id, 1)
        await cb.message.answer('Пользователь назначен администратором.',
                                reply_markup=kb.admin_menu_kb)
    await admin_reset(state)


@dp.message_handler(text='⛔👨‍💻 Удалить участника', state=SessionRole.admin)
async def remove_member(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    users = await sqlite_db.get_users()
    await msg.answer(text='<b>Выберите участника, которого хотите удалить:</b>\n\n',
                     reply_markup=(await kb.remove_member_kb(users)))
    await state.update_data(curr_users=users)
    await UserEdition.remove_member.set()


@dp.callback_query_handler(Text(startswith='rm_user_'), state=UserEdition.remove_member)
async def remove_user_pick(cb: CallbackQuery, state: FSMContext):
    user_index = int(cb.data[8:])
    data = await state.get_data()
    curr_users = data['curr_users']
    new_keyboard = await kb.remove_member_kb(curr_users, user_index)
    await state.update_data(member_index=user_index)
    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=cb.message.text,
                                reply_markup=new_keyboard)


@dp.callback_query_handler(text='approve_remove', state=UserEdition.remove_member)
async def approve_remove_member(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    data = await state.get_data()
    user_index = data['member_index']
    users = data['curr_users']
    user_id = users[user_index][0]
    await sqlite_db.remove_user_by_id(user_id)
    await cb.message.answer(f'Участник @{users[user_index][3]} удалён',
                            reply_markup=kb.admin_menu_kb)
    await admin_reset(state)


async def upd_selected_users(cb: CallbackQuery, state: FSMContext, text: str):
    user_index = int(cb.data[5:])

    data = await state.get_data()
    if 'selected_users' not in data:
        await state.update_data(selected_users=[])

    data = await state.get_data()
    users_indices = data['selected_users']

    if user_index in users_indices:
        users_indices.remove(user_index)
    else:
        users_indices.append(user_index)
    await state.update_data(selected_users=users_indices)
    curr_users = data['curr_users']
    new_keyboard = await kb.update_users_to_update_points(curr_users, users_indices)
    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=text,
                                reply_markup=new_keyboard)


@dp.message_handler(text='📊 Баллы', state=SessionRole.admin)
async def points(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    m = await msg.answer('Выберите действие:', reply_markup=kb.points_kb)
    await state.update_data(msg=m)


@dp.message_handler(text='📊 Начислить баллы', state=SessionRole.admin)
async def add_points(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    users = await sqlite_db.get_users()
    await msg.answer('Выберите одного или нескольких участников, кому хотите начислить баллы:',
                     reply_markup=(await kb.update_users_to_update_points(users)))
    await state.update_data(role_state=(await state.get_state()).split(':')[1],
                            curr_users=users)
    await Points.add.set()


@dp.callback_query_handler(Text(startswith='user_'), state=Points.add)
async def select_user_to_add_points(cb: CallbackQuery, state: FSMContext):
    await upd_selected_users(cb, state, 'Выберите одного или нескольких участников, кому хотите начислить баллы:')


@dp.callback_query_handler(text='next_step', state=Points.add)
async def enter_points_amount_to_add(cb: CallbackQuery):
    await cb.message.delete()
    await cb.message.answer(f'Введите количество баллов, которое необходимо начислить выбранным пользователям:',
                            reply_markup=kb.prev_step_reply_kb)
    await Points.add_amount.set()


@dp.message_handler(state=Points.add_amount)
async def listening_points_amount_to_add(msg: Message, state: FSMContext):
    try:
        points_amount = float(msg.text)
        data = await state.get_data()
        curr_users = data['curr_users']
        selected_users_indices = data['selected_users']
        for j, i in enumerate(selected_users_indices):
            user_id = curr_users[i][0]
            user_points = await sqlite_db.get_user_points(user_id)
            user_points += points_amount

            await sqlite_db.add_points_to_user(user_id, points_amount)

            await sqlite_db.update_user_points(user_id, user_points)
            if j == len(selected_users_indices) - 1:
                await msg.answer(f'<b>{points_amount}</b> баллов начислены участнику @{curr_users[i][3]}',
                                 reply_markup=kb.admin_menu_kb)
            else:
                await msg.answer(f'<b>{points_amount}</b> баллов начислены участнику @{curr_users[i][3]}')

        await admin_reset(state)
    except ValueError:
        await msg.answer('Введено недопустимое значение. Попробуйте еще раз.\n'
                         'Например: 5 или 2.5')


@dp.message_handler(text='🚫 Отнять баллы', state=SessionRole.admin)
async def reduce_points(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    users = await sqlite_db.get_users()
    await msg.answer('Выберите одного или несколько участников, у кого хотите отнять баллы:',
                     reply_markup=(await kb.update_users_to_update_points(users)))
    await state.update_data(role_state=(await state.get_state()).split(':')[1],
                            curr_users=users)
    await Points.reduce.set()


@dp.callback_query_handler(Text(startswith='user_'), state=Points.reduce)
async def select_user_to_reduce_points(cb: CallbackQuery, state: FSMContext):
    await upd_selected_users(cb, state, 'Выберите одного или нескольких участников, у кого хотите отнять баллы:')


@dp.callback_query_handler(text='next_step', state=Points.reduce)
async def enter_points_amount_to_reduce(cb: CallbackQuery):
    await cb.message.delete()
    await cb.message.answer(f'Введите количество баллов, которое необходимо отнять у выбранных пользователей:',
                            reply_markup=kb.prev_step_reply_kb)
    await Points.reduce_amount.set()


@dp.message_handler(state=Points.reduce_amount)
async def listening_points_amount_to_reduce(msg: Message, state: FSMContext):
    try:
        points_amount = float(msg.text)
        data = await state.get_data()
        curr_users = data['curr_users']
        selected_users_indices = data['selected_users']
        for j, i in enumerate(selected_users_indices):
            user_id = curr_users[i][0]
            user_points = await sqlite_db.get_user_points(user_id)
            user_points -= points_amount

            await sqlite_db.add_points_to_user(user_id, -1 * points_amount)

            await sqlite_db.update_user_points(user_id, user_points)
            if j == len(selected_users_indices) - 1:
                await msg.answer(f'<b>{points_amount}</b> баллов вычтены у пользователя @{curr_users[i][3]}',
                                 reply_markup=kb.admin_menu_kb)
            else:
                await msg.answer(f'<b>{points_amount}</b> баллов вычтены у пользователя @{curr_users[i][3]}')

        await admin_reset(state)
    except ValueError:
        await msg.answer('Введено недопустимое значение. Попробуйте еще раз.\n'
                         'Например: 5 или 2.5')


@dp.message_handler(text='↪️ Каналы', state=SessionRole.admin)
async def channels_action(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    await msg.answer('Выберите, какой канал хотите изменить:',
                     reply_markup=kb.channels_kb)
    await Channel.choose.set()


@dp.callback_query_handler(text='edit_request_channel', state=Channel.choose)
async def change_request_channel(cb: CallbackQuery):
    await cb.message.delete()
    await cb.message.answer('Вы пытаетесь изменить канал запросов 📝\n'
                            'Перешлите любое сообщение из канала:',
                            reply_markup=kb.prev_step_kb)
    await Channel.listening_request_channel.set()


@dp.message_handler(state=Channel.listening_request_channel)
async def listening_request_channel(msg: Message):
    channel_id = msg.forward_from_chat.id
    CONFIG['channels']['request_channel'] = channel_id
    with open('data/config.json', 'w', encoding='utf-8') as json_file:
        json.dump(CONFIG, json_file, ensure_ascii=False, indent=4)
    await msg.answer('Канал запросов успешно обновлен',
                     reply_markup=kb.admin_menu_kb)
    await SessionRole.admin.set()


@dp.callback_query_handler(text='edit_report_channel', state=Channel.choose)
async def change_report_channel(cb: CallbackQuery):
    await cb.message.delete()
    await cb.message.answer('Вы пытаетесь изменить канал отчётности 📩\n'
                            'Перешлите любое сообщение из канала:',
                            reply_markup=kb.prev_step_kb)
    await Channel.listening_report_channel.set()


@dp.message_handler(state=Channel.listening_report_channel)
async def listening_report_channel(msg: Message):
    channel_id = msg.forward_from_chat.id
    CONFIG['channels']['report_channel'] = channel_id
    with open('data/config.json', 'w', encoding='utf-8') as json_file:
        json.dump(CONFIG, json_file, ensure_ascii=False, indent=4)
    await msg.answer('Канал отчётности успешно обновлен',
                     reply_markup=kb.admin_menu_kb)
    await SessionRole.admin.set()


@dp.callback_query_handler(text='edit_goals_channel', state=Channel.choose)
async def change_goals_channel(cb: CallbackQuery):
    await cb.message.delete()
    await cb.message.answer('Вы пытаетесь изменить канал закрытых целей ✅\n'
                            'Перешлите любое сообщение из канала:',
                            reply_markup=kb.prev_step_kb)
    await Channel.listening_goals_channel.set()


@dp.message_handler(state=Channel.listening_goals_channel)
async def listening_goals_channel(msg: Message):
    channel_id = msg.forward_from_chat.id
    CONFIG['channels']['goals_channel'] = channel_id
    with open('data/config.json', 'w', encoding='utf-8') as json_file:
        json.dump(CONFIG, json_file, ensure_ascii=False, indent=4)
    await msg.answer('Канал закрытых целей успешно обновлен',
                     reply_markup=kb.admin_menu_kb)
    await SessionRole.admin.set()


@dp.message_handler(text='⛔📝 Удалить запрос', state=SessionRole.admin)
async def remove_request(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    requests = await sqlite_db.get_all_requests()
    await state.update_data(reqs=requests)
    await msg.answer('Выберите запрос, который хотите удалить:',
                     reply_markup=(await kb.users_requests_kb(requests)))
    await EditRequest.remove.set()


@dp.callback_query_handler(Text(startswith='elm_'), state=EditRequest.remove)
async def select_request_to_remove(cb: CallbackQuery, state: FSMContext):
    req_index = int(cb.data[4:])
    await cb.message.delete()
    data = await state.get_data()
    curr_request = data['reqs'][req_index]
    await state.update_data(curr_req=curr_request)
    await cb.message.answer(f'Вы пытаетесь удалить <b>Запрос #{curr_request[0]}</b>.\n'
                            f'Подтвердить удаление?',
                            reply_markup=kb.approve_removing_request_kb)
    await EditRequest.ask_confirm_removing.set()


@dp.callback_query_handler(text='approve_rem_req', state=EditRequest.ask_confirm_removing)
async def approve_removing_request(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    request = (await state.get_data())['curr_req']
    request_id = request[0]
    msg_id = request[8]
    await sqlite_db.remove_request_by_id(request_id)
    try:
        await bot.delete_message(chat_id=CONFIG['channels']['request_channel'],
                                 message_id=msg_id)
    except Exception as e:
        print(f'Channel which contains this request probably was changed.\n{e}')
    await cb.message.answer('Запрос успешно удалён ✅',
                            reply_markup=kb.admin_menu_kb)
    await admin_reset(state)


@dp.callback_query_handler(text='cancel_rem_req', state=EditRequest.ask_confirm_removing)
async def cancel_removing_request(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await cb.message.answer('Удаление запроса отменено ❌',
                            reply_markup=kb.admin_menu_kb)
    await admin_reset(state)


@dp.message_handler(text='👑 Изменить статус', state=SessionRole.admin)
async def change_status(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    users = await sqlite_db.get_users()
    await msg.answer(text='<b>Выберите участника, у которого хотите изменить статус:</b>\n\n',
                     reply_markup=(await kb.select_member_to_edit_status_kb(users)))
    await state.update_data(curr_users=users)
    await UserEdition.edit_status.set()


@dp.callback_query_handler(Text(startswith='user_'), state=UserEdition.edit_status)
async def change_user_status_pick(cb: CallbackQuery, state: FSMContext):
    user_index = int(cb.data[5:])
    data = await state.get_data()
    curr_users = data['curr_users']
    new_keyboard = await kb.select_member_to_edit_status_kb(curr_users, user_index)
    await state.update_data(user_index=user_index)
    await bot.edit_message_text(chat_id=cb.message.chat.id,
                                message_id=cb.message.message_id,
                                text=cb.message.text,
                                reply_markup=new_keyboard)


@dp.callback_query_handler(text='next_step', state=UserEdition.edit_status)
async def choose_status(cb: CallbackQuery):
    await cb.message.delete()
    await cb.message.answer('Выберите новый статус:',
                            reply_markup=(await kb.user_status_kb()))


@dp.callback_query_handler(Text(startswith='elm_'), state=UserEdition.edit_status)
async def finish_user_status_edition(cb: CallbackQuery, state: FSMContext):
    status_index = int(cb.data[4:])
    await cb.message.delete()
    data = await state.get_data()
    users = data['curr_users']
    user = users[data['user_index']]
    user_id = user[0]
    new_status = STATUS[list(STATUS.keys())[status_index]]['value']
    await sqlite_db.update_user_status(user_id, new_status)

    user_reports = await sqlite_db.get_user_reports(user_id)
    for report in user_reports:
        report_id = report[0]
        try:
            await update_report_message(report_id)
        except (MessageToEditNotFound, MessageIdInvalid):
            await sqlite_db.remove_report_by_id(report_id)

    all_requests = await sqlite_db.get_all_requests()
    for request in all_requests:
        if requestContainsUser(request, user):
            request_id = request[0]
            try:
                await update_request_message(request_id)
            except (MessageToEditNotFound, MessageIdInvalid):
                await sqlite_db.remove_request_by_id(request_id)

    await cb.message.answer(f'Статус пользователя @{user[3]} успешно обновлён.',
                            reply_markup=kb.admin_menu_kb)
    await admin_reset(state)

