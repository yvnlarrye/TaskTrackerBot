import asyncio

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)

from dispatcher import dp, bot
from keyboards import keyboards as kb
from keyboards.keyboards import apply_tasks_kb
from utils.reports import print_report, update_report_data
from utils.request import (
    request_to_user, request_from_user, commit_request, request_date,
    print_request, update_request_message, request_time
)
from utils.utils import (
    format_recipients, format_addressers, commit_report, delete_prev_message, refresh_role
)
from states import SessionRole, CreateRequest, CreateReport, UserEdition, EditRequest, EditReport
from datetime import datetime

from utils.validators import parse_time, validate_time
from data import sqlite_db
from data.config import REQUEST_STATUS, CONFIG


async def member_start(msg: Message, state: FSMContext):
    m = await msg.answer(text='Главное меню:',
                         reply_markup=kb.member_menu_kb)
    await state.reset_data()
    await state.update_data(msg=m)
    await SessionRole.member.set()


@dp.message_handler(text='↩️ Вернуться назад', state=[SessionRole.member, CreateRequest.text,
                                                      CreateRequest.time, CreateRequest.date,
                                                      CreateReport.earned,
                                                      EditRequest.date, EditRequest.text,
                                                      EditRequest.status])
async def back_to_member_menu(msg: Message, state: FSMContext):
    await member_start(msg, state)


@dp.callback_query_handler(text='prev_step', state=[SessionRole.member, EditRequest.select_member_request,
                                                    EditRequest.select_request_headers,
                                                    EditRequest.time, EditRequest.status,
                                                    EditRequest.addressers, EditRequest.recipients,
                                                    CreateRequest.request_from, CreateRequest.request_to,
                                                    CreateRequest.time,
                                                    CreateReport.list_of_done_tasks,
                                                    CreateReport.list_of_not_done_tasks,
                                                    CreateReport.list_of_scheduled_tasks,
                                                    ])
async def back_to_member_menu_kb(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await delete_prev_message(cb.from_user.id, state)
    await member_start(cb.message, state)


@dp.message_handler(state=UserEdition.new_admin_name)
async def new_admin_name(msg: Message):
    text = msg.text.split()
    if len(text) == 2:
        name = text[0]
        surname = text[1]
        await sqlite_db.add_admin(msg.from_id, msg.from_user.username, name, surname)
        await msg.answer('Новый администратор добавлен',
                         reply_markup=kb.admin_menu_kb)
        await SessionRole.admin.set()


@dp.message_handler(text='📝 Запрос', state=SessionRole.member)
async def request(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    users = await sqlite_db.get_users()
    await state.update_data(curr_users=users)
    await msg.answer(text=(await format_addressers(users)),
                     reply_markup=(await kb.update_addressers_kb(users)))
    await CreateRequest.request_from.set()


@dp.callback_query_handler(Text(startswith='user_'), state=CreateRequest.request_from)
async def create_request_from_user(cb: CallbackQuery, state: FSMContext):
    await request_from_user(cb, state)


@dp.callback_query_handler(text='next_step', state=CreateRequest.request_from)
async def pick_recipients(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    users = (await state.get_data())['curr_users']
    await cb.message.answer(text=(await format_recipients(users)),
                            reply_markup=(await kb.update_recipients_kb(users)))
    await delete_prev_message(cb.from_user.id, state)
    await CreateRequest.request_to.set()


@dp.callback_query_handler(Text(startswith='user_'), state=CreateRequest.request_to)
async def create_request_to_user(cb: CallbackQuery, state: FSMContext):
    await request_to_user(cb, state)


@dp.callback_query_handler(text='next_step', state=CreateRequest.request_to)
async def set_request_text(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'request_to' not in data or len(data['request_to']) == 0:
        m = await cb.message.answer('Необходимо выбрать хотя бы одного исполнителя')
        await asyncio.sleep(2)
        await m.delete()
    else:
        await cb.message.delete()
        await cb.message.answer('Введите текст запроса:',
                                reply_markup=kb.prev_step_reply_kb)
        await delete_prev_message(cb.from_user.id, state)
        await CreateRequest.text.set()


@dp.message_handler(state=CreateRequest.text)
async def listening_request_text(msg: Message, state: FSMContext):
    await state.update_data(text=msg.text)
    await msg.answer(f'Введите дату срока запроса в формате:\n'
                     f'DD.MM.YY\n'
                     f'Например: {datetime.now().strftime("%d.%m.%y")}',
                     reply_markup=kb.prev_step_reply_kb)
    await CreateRequest.date.set()


@dp.message_handler(state=CreateRequest.date)
async def listening_request_date(msg: Message, state: FSMContext):
    await request_date(msg, state, CreateRequest.time)


@dp.message_handler(state=CreateRequest.time)
async def listening_request_time(msg: Message, state: FSMContext):
    try:
        result = parse_time(msg.text)
        await validate_time(result)
        await state.update_data(time=result)
        await state.update_data(author_telegram_id=msg.from_id)

        await msg.answer('Для завершения операции нажмите кнопку "Подтвердить"',
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_request')
                         ).add(
                             InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
                         )
                         )
    except AttributeError:
        await msg.answer(text='Неверный формат времени')
        await msg.answer(f'Введите время:\n'
                         f'Например: {datetime.now().strftime("%H:%M")}')


@dp.callback_query_handler(text='confirm_request', state=CreateRequest.time)
async def confirm_creating_request(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await commit_request(data)
    author_id = await sqlite_db.get_user_id(data['author_telegram_id'])
    request_id = (await sqlite_db.get_user_last_request_id(author_id))[0]
    users = data['curr_users']
    addressers = [
        (users[user_index][3], users[user_index][4], users[user_index][5], users[user_index][7],)
        for user_index in data['request_from']
    ]
    main_recipient = users[data['main_recipient']]
    main_recipient = (main_recipient[3], main_recipient[4], main_recipient[5], main_recipient[7],)
    secondary_recipients = [
        (users[user_index][3], users[user_index][4], users[user_index][5], users[user_index][7],)
        for user_index in data['secondary_recipients']
    ]
    output = print_request(request_id=request_id,
                           status=REQUEST_STATUS['in_progress'],
                           addressers=addressers,
                           main_recipient=main_recipient,
                           secondary_recipients=secondary_recipients,
                           text=data['text'],
                           date=data['date'],
                           time=data['time'])
    await cb.message.answer(output,
                            reply_markup=kb.member_menu_kb)
    await cb.message.delete()
    msg = await bot.send_message(chat_id=CONFIG['request_channel'],
                                 text=output)
    await sqlite_db.add_message_id_to_request(request_id, msg.message_id)

    await state.finish()
    await SessionRole.member.set()


@dp.message_handler(text='✏️ Ред. запрос', state=SessionRole.member)
async def edit_request_by_member(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    user_id = await sqlite_db.get_user_id(msg.from_id)
    await state.update_data(role_state=(await state.get_state()).split(':')[1])
    requests = await sqlite_db.get_user_requests(user_id)
    if len(requests):
        await state.update_data(user_id=user_id, reqs=requests)
        await msg.answer('Выберите запрос для редактирования:',
                         reply_markup=(await kb.users_requests_kb(requests)))
        await EditRequest.select_member_request.set()
    else:
        await msg.answer('Этот участник еще не создал ни одного запроса.',
                         reply_markup=kb.prev_step_reply_kb)


@dp.callback_query_handler(Text(startswith='elm_'), state=EditRequest.select_member_request)
async def select_member_request(cb: CallbackQuery, state: FSMContext):
    req_index = int(cb.data[4:])
    await cb.message.delete()
    data = await state.get_data()
    requests = data['reqs']
    await state.update_data(req=requests[req_index])
    await cb.message.answer('Выберите поле запроса, которое хотите отредактировать:',
                            reply_markup=(await kb.request_headers_kb()))
    await EditRequest.select_request_headers.set()


@dp.callback_query_handler(Text(startswith='elm_'), state=EditRequest.select_request_headers)
async def select_request_headers(cb: CallbackQuery, state: FSMContext):
    header_index = int(cb.data[4:])
    await cb.message.delete()
    match header_index:
        case 0:
            await cb.message.answer('Выберите статус:',
                                    reply_markup=(await kb.request_status_kb()))
            await EditRequest.status.set()
        case 1:
            users = await sqlite_db.get_users()
            await state.update_data(curr_users=users)
            await cb.message.answer(f'{(await format_addressers(users))}',
                                    reply_markup=(await kb.update_addressers_kb(users)))
            await EditRequest.addressers.set()
        case 2:
            users = await sqlite_db.get_users()
            await state.update_data(curr_users=users)
            await cb.message.answer(f'{(await format_recipients(users))}',
                                    reply_markup=(await kb.update_recipients_kb(users)))
            await EditRequest.recipients.set()
        case 3:
            await cb.message.answer('Введите текст запроса:',
                                    reply_markup=kb.prev_step_reply_kb)
            await EditRequest.text.set()
        case 4:
            await cb.message.answer(f'Введите дату напоминания в формате:\n'
                                    f'DD.MM.YY\n'
                                    f'Например: {datetime.now().strftime("%d.%m.%y")}',
                                    reply_markup=kb.prev_step_reply_kb)
            await EditRequest.date.set()


@dp.callback_query_handler(Text(startswith='elm_'), state=EditRequest.status)
async def edit_request_status(cb: CallbackQuery, state: FSMContext):
    status = int(cb.data[4:])
    await cb.message.delete()
    data = await state.get_data()
    curr_request = data['req']
    request_id = curr_request[0]
    request_status = curr_request[2]

    if status == request_status:
        await cb.message.answer('Запрос уже имеет такой статус',
                                reply_markup=kb.prev_step_reply_kb)
        return

    secondary_recipients = curr_request[5]
    main_recipient_id = (await sqlite_db.get_member_by_username(curr_request[4]))[0]
    secondary_recipients_ids = []
    if secondary_recipients != '':
        secondary_recipients_ids = [
            (await sqlite_db.get_member_by_username(username))[0]
            for username in secondary_recipients.split('\n')
        ]
    main_recipient_rate = await sqlite_db.get_user_points(main_recipient_id)

    sign = None
    if status != 2 and request_status == 2:
        sign = -1
    if status == 2 and request_status != 2:
        sign = 1
    if sign is not None:
        main_recipient_rate += 1 * sign
        await sqlite_db.update_user_points(main_recipient_id, main_recipient_rate)
        for recipient_id in secondary_recipients_ids:
            recipient_rate = await sqlite_db.get_user_points(recipient_id)
            recipient_rate += 0.5 * sign
            await sqlite_db.update_user_points(recipient_id, recipient_rate)

    await sqlite_db.update_request_status(request_id, status)
    await update_request_message(request_id)

    await cb.message.answer('Статус запроса успешно обновлён',
                            reply_markup=kb.member_menu_kb)
    await SessionRole.member.set()


@dp.callback_query_handler(Text(startswith='user_'), state=EditRequest.addressers)
async def edit_addressers(cb: CallbackQuery, state: FSMContext):
    await request_from_user(cb, state)


@dp.callback_query_handler(text='next_step', state=EditRequest.addressers)
async def confirm_edit_addressers(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = data['curr_users']
    request_id = data['req'][0]
    addressers = '\n'.join([users[user_index][3] for user_index in data['request_from']])
    await sqlite_db.update_request_addressers(request_id, addressers)

    await update_request_message(request_id)

    await cb.message.answer('Отправители запроса успешно изменены',
                            reply_markup=kb.member_menu_kb)
    await cb.message.delete()
    await SessionRole.member.set()


@dp.callback_query_handler(Text(startswith='user_'), state=EditRequest.recipients)
async def edit_recipients(cb: CallbackQuery, state: FSMContext):
    await request_to_user(cb, state)


@dp.callback_query_handler(text='next_step', state=EditRequest.recipients)
async def confirm_edit_recipients(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'request_to' not in data or len(data['request_to']) == 0:
        await cb.message.answer('Необходимо выбрать хотя бы одного исполнителя')
    else:
        users = data['curr_users']
        request_id = data['req'][0]
        main_recipient = users[data['main_recipient']][3]
        secondary_recipients = '\n'.join([users[user_index][3] for user_index in data['secondary_recipients']])
        await sqlite_db.update_request_recipients(request_id, main_recipient, secondary_recipients)
        await update_request_message(request_id)
        await cb.message.answer('Получатели успешно изменены.',
                                reply_markup=kb.member_menu_kb)
        await cb.message.delete()
        await SessionRole.member.set()


@dp.message_handler(state=EditRequest.text)
async def edit_text(msg: Message, state: FSMContext):
    text = msg.text
    data = await state.get_data()
    request_id = data['req'][0]
    await sqlite_db.update_request_text(request_id, text)

    await update_request_message(request_id)

    await msg.answer('Текст запроса успешно изменен',
                     reply_markup=kb.member_menu_kb)
    await SessionRole.member.set()


@dp.message_handler(state=EditRequest.date)
async def edit_date(msg: Message, state: FSMContext):
    await request_date(msg, state, EditRequest.time)


@dp.message_handler(state=EditRequest.time)
async def edit_time(msg: Message, state: FSMContext):
    await request_time(msg, state)


@dp.message_handler(text='📩 Отчетность', state=SessionRole.member)
async def reporting(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    await msg.answer('Сколько заработали 💰₽ за сегодняшний день?\n'
                     'Введите значение в следующем формате: 150000',
                     reply_markup=kb.prev_step_reply_kb)
    await CreateReport.earned.set()


@dp.message_handler(state=CreateReport.earned)
async def add_phone_time(msg: Message, state: FSMContext):
    try:
        result = int(msg.text)
        message = await msg.answer('✅ Введите список выполненных сегодня задач (по одной):',
                                   reply_markup=apply_tasks_kb())
        await state.update_data(earned=result, user_id=msg.from_id, msg_id=message.message_id,
                                done_tasks_list=[])
        await CreateReport.list_of_done_tasks.set()
    except ValueError:
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.')


@dp.message_handler(state=CreateReport.list_of_done_tasks)
async def listening_done_tasks(msg: Message, state: FSMContext):
    data = await state.get_data()
    done_tasks_list = data['done_tasks_list']
    done_tasks_list.append(msg.text)
    await state.update_data(done_tasks_list=done_tasks_list)
    data = await state.get_data()
    append_text = '\n'.join(['- ' + task for task in data['done_tasks_list']])
    await bot.edit_message_text(text=f"✅ Введите список выполненных сегодня задач (по одной):\n\n"
                                     f"{append_text}",
                                chat_id=msg.from_id,
                                message_id=data['msg_id'],
                                reply_markup=apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=CreateReport.list_of_done_tasks)
async def apply_done_tasks(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    message = await cb.message.answer('❌ Введите список не выполненных сегодня задач (по одной):',
                                      reply_markup=apply_tasks_kb())
    await state.update_data(msg_id=message.message_id,
                            not_done_tasks_list=[])
    await CreateReport.list_of_not_done_tasks.set()


@dp.message_handler(state=CreateReport.list_of_not_done_tasks)
async def listening_not_done_tasks(msg: Message, state: FSMContext):
    data = await state.get_data()
    not_done_tasks_list = data['not_done_tasks_list']
    not_done_tasks_list.append(msg.text)
    await state.update_data(not_done_tasks_list=not_done_tasks_list)
    data = await state.get_data()
    append_text = '\n'.join(['- ' + task for task in data['not_done_tasks_list']])
    await bot.edit_message_text(text=f"❌ Введите список не выполненных сегодня задач (по одной):\n\n"
                                     f"{append_text}",
                                chat_id=msg.from_id,
                                message_id=data['msg_id'],
                                reply_markup=apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=CreateReport.list_of_not_done_tasks)
async def apply_not_done_tasks(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    message = await cb.message.answer('📝 Введите список запланированных на завтра задач (по одной):',
                                      reply_markup=apply_tasks_kb())
    await state.update_data(msg_id=message.message_id,
                            scheduled_tasks_list=[])
    await CreateReport.list_of_scheduled_tasks.set()


@dp.message_handler(state=CreateReport.list_of_scheduled_tasks)
async def listening_scheduled_tasks(msg: Message, state: FSMContext):
    data = await state.get_data()
    scheduled_tasks_list = data['scheduled_tasks_list']
    scheduled_tasks_list.append(msg.text)
    await state.update_data(scheduled_tasks_list=scheduled_tasks_list)
    data = await state.get_data()
    append_text = '\n'.join(['- ' + task for task in data['scheduled_tasks_list']])
    await bot.edit_message_text(text=f"📝 Введите список запланированных на завтра задач (по одной):\n\n"
                                     f"{append_text}",
                                chat_id=msg.from_id,
                                message_id=data['msg_id'],
                                reply_markup=apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=CreateReport.list_of_scheduled_tasks)
async def apply_scheduled_tasks(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    data = await state.get_data()
    await commit_report(data)

    author_id = await sqlite_db.get_user_id(cb.from_user.id)
    report_id = (await sqlite_db.get_user_last_report_id(author_id))[0]
    member = await sqlite_db.get_user_by_id(author_id)
    surname = member[5]
    first_name = member[4]
    user_name = member[3]
    earned = data['earned']
    done_tasks = data['done_tasks_list']
    not_done_tasks = data['not_done_tasks_list']
    scheduled_tasks = data['scheduled_tasks_list']

    output = await print_report(report_id=report_id,
                                surname=surname,
                                first_name=first_name,
                                username=user_name,
                                earned=earned,
                                done_tasks=done_tasks,
                                not_done_tasks=not_done_tasks,
                                scheduled_tasks=scheduled_tasks)

    await cb.message.answer(output)
    msg = await bot.send_message(chat_id=CONFIG['report_channel'],
                                 text=output)
    await sqlite_db.add_message_id_to_report(report_id, msg.message_id)
    await state.finish()
    await SessionRole.member.set()


@dp.message_handler(text='✏️ Ред. отчётность', state=SessionRole.member)
async def edit_member_report(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    user_id = await sqlite_db.get_user_id(msg.from_id)
    await state.update_data(role_state=(await state.get_state()).split(':')[1])
    reports = await sqlite_db.get_user_reports(user_id)
    if len(reports):
        await state.update_data(user_id=user_id)
        await msg.answer('Выберите отчёт для редактирования:',
                         reply_markup=(await kb.member_reports_kb(reports)))
        await EditReport.select_member_report.set()
    else:
        await msg.answer('Этот участник еще не создал ни одного отчёта.',
                         reply_markup=kb.prev_step_reply_kb)


@dp.callback_query_handler(Text(startswith='elm_'), state=EditReport.select_member_report)
async def select_member_report(cb: CallbackQuery, state: FSMContext):
    rep_index = int(cb.data[4:])
    await state.update_data(rep_index=rep_index)
    await cb.message.answer('Выберите поле отчёта, которое хотите отредактировать:',
                            reply_markup=(await kb.report_headers_kb()))
    await EditReport.select_report_headers.set()


@dp.callback_query_handler(Text(startswith='elm_'), state=EditReport.select_report_headers)
async def select_report_headers(cb: CallbackQuery, state: FSMContext):
    header_index = int(cb.data[4:])
    await cb.message.delete()
    match header_index:
        case 0:
            await cb.message.answer('Введите количество времени, проведенное в телефоне за день.\n'
                                    'Например: 00:25 или 01:19')
            await EditReport.phone_time.set()
        case 1:
            message = await cb.message.answer('✅ Введите список выполненных сегодня задач (по одной):',
                                              reply_markup=apply_tasks_kb())
            await state.update_data(done_tasks_list=[], message_id=message.message_id)
            await EditReport.list_of_done_tasks.set()
        case 2:
            message = await cb.message.answer('❌ Введите список не выполненных сегодня задач (по одной):',
                                              reply_markup=apply_tasks_kb())
            await state.update_data(not_done_tasks_list=[], message_id=message.message_id)
            await EditReport.list_of_not_done_tasks.set()
        case 3:
            message = await cb.message.answer('📝 Введите список запланированных на завтра задач (по одной):',
                                              reply_markup=apply_tasks_kb())
            await state.update_data(scheduled_tasks_list=[], message_id=message.message_id)
            await EditReport.list_of_scheduled_tasks.set()


@dp.message_handler(state=EditReport.phone_time)
async def edit_phone_time(msg: Message, state: FSMContext):
    try:
        phone_time = parse_time(msg.text)
        await validate_time(phone_time)

        data = await state.get_data()
        reports = await sqlite_db.get_user_reports(data['user_id'])
        report_id = reports[data['rep_index']][0]
        await sqlite_db.update_report_phone_time(report_id, phone_time)

        await update_report_data(report_id)

        await msg.answer('Активность в телефоне успешно изменена')
        await refresh_role(state)

    except AttributeError:
        await msg.answer(text='Неверный формат времени')
        await msg.answer(f'Введите время:\n'
                         f'Например: {datetime.now().strftime("%H:%M")}')


@dp.message_handler(state=EditReport.list_of_done_tasks)
async def edit_list_of_done_tasks(msg: Message, state: FSMContext):
    data = await state.get_data()
    done_tasks_list = data['done_tasks_list']
    done_tasks_list.append(msg.text)
    await state.update_data(done_tasks_list=done_tasks_list)
    append_text = '\n'.join(['- ' + task for task in data['done_tasks_list']])
    await bot.edit_message_text(text=f"✅ Введите список выполненных сегодня задач (по одной):\n\n"
                                     f"{append_text}",
                                chat_id=msg.from_id,
                                message_id=data['message_id'],
                                reply_markup=apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=EditReport.list_of_done_tasks)
async def apply_edition_done_tasks(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    done_tasks = '\n'.join(data['done_tasks_list'])
    reports = await sqlite_db.get_user_reports(data['user_id'])
    report_id = reports[data['rep_index']][0]
    await sqlite_db.update_report_done_tasks(report_id, done_tasks)

    await update_report_data(report_id)

    await cb.message.answer('Выполненные задания успешно изменены')
    await refresh_role(state)


@dp.message_handler(state=EditReport.list_of_not_done_tasks)
async def edit_list_of_not_done_tasks(msg: Message, state: FSMContext):
    data = await state.get_data()
    not_done_tasks_list = data['not_done_tasks_list']
    not_done_tasks_list.append(msg.text)
    await state.update_data(not_done_tasks_list=not_done_tasks_list)
    append_text = '\n'.join(['- ' + task for task in data['not_done_tasks_list']])
    await bot.edit_message_text(text=f"❌ Введите список не выполненных сегодня задач (по одной):\n\n"
                                     f"{append_text}",
                                chat_id=msg.from_id,
                                message_id=data['message_id'],
                                reply_markup=apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=EditReport.list_of_not_done_tasks)
async def apply_edition_not_done_tasks(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    not_done_tasks = '\n'.join(data['not_done_tasks_list'])
    reports = await sqlite_db.get_user_reports(data['user_id'])
    report_id = reports[data['rep_index']][0]
    await sqlite_db.update_report_not_done_tasks(report_id, not_done_tasks)

    await update_report_data(report_id)

    await cb.message.answer('Не выполненные задания успешно изменены')
    await refresh_role(state)


@dp.message_handler(state=EditReport.list_of_scheduled_tasks)
async def edit_list_of_scheduled_tasks(msg: Message, state: FSMContext):
    data = await state.get_data()
    scheduled_tasks = data['scheduled_tasks_list']
    scheduled_tasks.append(msg.text)
    await state.update_data(scheduled_tasks_list=scheduled_tasks)
    append_text = '\n'.join(['- ' + task for task in data['scheduled_tasks_list']])
    await bot.edit_message_text(text=f"📝 Введите список запланированных на завтра задач (по одной):\n\n"
                                     f"{append_text}",
                                chat_id=msg.from_id,
                                message_id=data['message_id'],
                                reply_markup=apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=EditReport.list_of_scheduled_tasks)
async def apply_edition_scheduled_tasks(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    scheduled_tasks = '\n'.join(data['scheduled_tasks_list'])
    reports = await sqlite_db.get_user_reports(data['user_id'])
    report_id = reports[data['rep_index']][0]
    await sqlite_db.update_report_scheduled_tasks(report_id, scheduled_tasks)

    await update_report_data(report_id)

    await cb.message.answer('Запланированные задания успешно изменены')
    await refresh_role(state)
