import asyncio
import re

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.markdown import hlink

from dispatcher import dp, bot
from keyboards import keyboards as kb
from keyboards.keyboards import apply_tasks_kb
from utils.reports import print_report, update_report_message
from utils.request import (
    request_to_user, request_from_user, commit_request, print_request, update_request_message
)
from utils.utils import (
    format_recipients, format_addressers, commit_report, delete_prev_message, get_status_icon
)
from states import SessionRole, CreateRequest, CreateReport, UserEdition, EditRequest, EditReport, Goals
from datetime import datetime

from utils.validators import validate_date
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
                                                      EditRequest.status, EditReport.earned,
                                                      Goals.days, Goals.media, Goals.check_amount,
                                                      Goals.notion_link, Goals.comment])
async def back_to_member_menu_kb(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
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
                                                    EditReport.list_of_done_tasks,
                                                    EditReport.list_of_not_done_tasks,
                                                    EditReport.list_of_scheduled_tasks,
                                                    EditReport.select_report_headers,
                                                    EditReport.select_member_report
                                                    ])
async def back_to_member_menu_cb(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    await member_start(cb.message, state)


async def member_reset(state: FSMContext):
    await state.reset_data()
    await SessionRole.member.set()


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
    try:
        date = re.sub(r"[/\\-]", ".", re.search(r"(\d+.*?\d+.*?\d+)", msg.text).group(1))
        await validate_date(date, msg)
        await state.update_data(date=date)
        await msg.answer('Для завершения операции нажмите кнопку "Подтвердить"',
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_request')
                         ).add(
                             InlineKeyboardButton(text='↩️ Вернуться назад', callback_data='prev_step')
                         )
                         )
    except AttributeError:
        await msg.answer(text='Неверный формат даты',
                         reply_markup=kb.prev_step_reply_kb)
        await msg.answer(f'Введите дату срока запроса в формате:\n'
                         f'DD.MM.YY\n'
                         f'Например: {datetime.now().strftime("%d.%m.%y")}')


@dp.callback_query_handler(text='confirm_request', state=CreateRequest.date)
async def confirm_creating_request(cb: CallbackQuery, state: FSMContext):
    await state.update_data(author_telegram_id=cb.from_user.id)
    data = await state.get_data()
    await commit_request(data)
    author_id = await sqlite_db.get_user_id(cb.from_user.id)
    request_id = (await sqlite_db.get_user_last_request_id(author_id))[0]
    data = await state.get_data()
    users = data['curr_users']
    addressers = [
        (users[user_index][3], users[user_index][4], users[user_index][5], users[user_index][7],)
        for user_index in data['request_from']
    ]
    main_recipient = users[data['main_recipient']]
    main_recipient = (main_recipient[3], main_recipient[4], main_recipient[5], main_recipient[7],)
    if 'secondary_recipient' in data:
        secondary_recipient = users[data['secondary_recipient']]
        secondary_recipient = (
            secondary_recipient[3], secondary_recipient[4], secondary_recipient[5], secondary_recipient[7],
        )
    else:
        secondary_recipient = ()
    output = print_request(request_id=request_id,
                           status=REQUEST_STATUS['in_progress'],
                           addressers=addressers,
                           main_recipient=main_recipient,
                           secondary_recipient=secondary_recipient,
                           text=data['text'],
                           date=data['date'])
    await cb.message.answer(output,
                            reply_markup=kb.member_menu_kb)
    await cb.message.delete()
    msg = await bot.send_message(chat_id=CONFIG['channels']['request_channel'],
                                 text=output)
    await sqlite_db.add_message_id_to_request(request_id, msg.message_id)

    await member_reset(state)


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

    sign = None
    if status != 2 and request_status == 2:
        sign = -1
    if status == 2 and request_status != 2:
        sign = 1

    if sign is not None:
        main_recipient_id = (await sqlite_db.get_user_by_username(curr_request[4]))[0]
        main_recipient_rate = await sqlite_db.get_user_points(main_recipient_id)
        main_recipient_rate += 1 * sign
        await sqlite_db.update_user_points(main_recipient_id, main_recipient_rate)

        secondary_recipient = curr_request[5]
        if secondary_recipient != '':
            secondary_recipient_id = (await sqlite_db.get_user_by_username(curr_request[5]))[0]
            recipient_rate = await sqlite_db.get_user_points(secondary_recipient_id)
            recipient_rate += 0.5 * sign
            await sqlite_db.update_user_points(secondary_recipient_id, recipient_rate)

    await sqlite_db.update_request_status(request_id, status)
    await update_request_message(request_id)

    await cb.message.answer('Статус запроса успешно обновлён',
                            reply_markup=kb.member_menu_kb)
    await member_reset(state)


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
    await member_reset(state)


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
        if 'secondary_recipient' in data:
            secondary_recipient = users[data['secondary_recipient']][3]
        else:
            secondary_recipient = ''
        await sqlite_db.update_request_recipients(request_id, main_recipient, secondary_recipient)
        await update_request_message(request_id)
        await cb.message.answer('Получатели успешно изменены.',
                                reply_markup=kb.member_menu_kb)
        await cb.message.delete()
        await member_reset(state)


@dp.message_handler(state=EditRequest.text)
async def edit_text(msg: Message, state: FSMContext):
    text = msg.text
    data = await state.get_data()
    request_id = data['req'][0]
    await sqlite_db.update_request_text(request_id, text)

    await update_request_message(request_id)

    await msg.answer('Текст запроса успешно изменен',
                     reply_markup=kb.member_menu_kb)
    await member_reset(state)


@dp.message_handler(state=EditRequest.date)
async def edit_date(msg: Message, state: FSMContext):
    try:
        date = re.sub(r"[/\\-]", ".", re.search(r"(\d+.*?\d+.*?\d+)", msg.text).group(1))
        await validate_date(date, msg)
        data = await state.get_data()
        request_id = data['req'][0]
        await sqlite_db.update_request_date(request_id, date)
        await update_request_message(request_id)

        await msg.answer('Срок успешно изменен.',
                         reply_markup=kb.member_menu_kb)
        await member_reset(state)
    except AttributeError:
        date = datetime.now().strftime('%d.%m.%y')
        await msg.answer(text='Неверный формат даты',
                         reply_markup=kb.prev_step_reply_kb)
        await msg.answer(f'Введите дату срока запроса в формате:\n'
                         f'DD.MM.YY\n'
                         f'Например: {date}')


@dp.message_handler(text='📩 Отчетность', state=SessionRole.member)
async def reporting(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    m = await msg.answer('Сколько заработали 💰₽ за сегодняшний день?\n'
                         'Введите значение в следующем формате: 150000',
                         reply_markup=kb.prev_step_reply_kb)
    await state.update_data(msg=m)
    await CreateReport.earned.set()


@dp.message_handler(state=CreateReport.earned)
async def add_phone_time(msg: Message, state: FSMContext):
    try:
        result = int(msg.text)
        await delete_prev_message(msg.from_id, state)
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
    user = await sqlite_db.get_user_by_id(author_id)
    surname = user[5]
    first_name = user[4]
    user_name = user[3]
    user_status = user[7]
    earned = data['earned']
    done_tasks = data['done_tasks_list']
    not_done_tasks = data['not_done_tasks_list']
    scheduled_tasks = data['scheduled_tasks_list']

    user = (user_name, first_name, surname, user_status,)
    output = await print_report(report_id=report_id,
                                user=user,
                                earned=earned,
                                done_tasks=done_tasks,
                                not_done_tasks=not_done_tasks,
                                scheduled_tasks=scheduled_tasks)

    await cb.message.answer(output, reply_markup=kb.member_menu_kb)
    msg = await bot.send_message(chat_id=CONFIG['channels']['report_channel'],
                                 text=output)
    await sqlite_db.add_message_id_to_report(report_id, msg.message_id)
    await member_reset(state)


@dp.message_handler(text='✏️ Ред. отчётность', state=SessionRole.member)
async def edit_user_report(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    user_id = await sqlite_db.get_user_id(msg.from_id)
    await state.update_data(role_state=(await state.get_state()).split(':')[1])
    reports = await sqlite_db.get_user_reports(user_id)
    if len(reports):
        await state.update_data(user_id=user_id, reps=reports)
        await msg.answer('Выберите отчёт для редактирования:',
                         reply_markup=(await kb.member_reports_kb(reports)))
        await EditReport.select_member_report.set()
    else:
        await msg.answer('Этот участник еще не создал ни одного отчёта.',
                         reply_markup=kb.prev_step_reply_kb)


@dp.callback_query_handler(Text(startswith='elm_'), state=EditReport.select_member_report)
async def select_member_report(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    rep_index = int(cb.data[4:])
    await state.update_data(rep=(await state.get_data())['reps'][rep_index])
    await cb.message.answer('Выберите поле отчёта, которое хотите отредактировать:',
                            reply_markup=(await kb.report_headers_kb()))
    await EditReport.select_report_headers.set()


@dp.callback_query_handler(Text(startswith='elm_'), state=EditReport.select_report_headers)
async def select_report_headers(cb: CallbackQuery, state: FSMContext):
    header_index = int(cb.data[4:])
    await cb.message.delete()
    match header_index:
        case 0:
            m = await cb.message.answer('Сколько заработали 💰₽ за сегодняшний день?\n'
                                        'Введите значение в следующем формате: 150000',
                                        reply_markup=kb.prev_step_reply_kb)
            await state.update_data(msg=m)
            await EditReport.earned.set()
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


@dp.message_handler(state=EditReport.earned)
async def edit_phone_time(msg: Message, state: FSMContext):
    try:
        result = int(msg.text)
        await delete_prev_message(msg.from_id, state)
        data = await state.get_data()
        report = data['rep']
        report_id = report[0]
        await sqlite_db.update_report_earned(report_id, result)

        await update_report_message(report_id)

        await msg.answer('<b>Заработанная сумма</b> успешно изменена',
                         reply_markup=kb.member_menu_kb)
        await member_reset(state)

    except ValueError:
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.')


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
    await cb.message.delete()
    data = await state.get_data()
    done_tasks = '\n'.join(data['done_tasks_list'])
    report_id = data['rep'][0]
    await sqlite_db.update_report_done_tasks(report_id, done_tasks)

    await update_report_message(report_id)

    await cb.message.answer('Выполненные задания успешно изменены',
                            reply_markup=kb.member_menu_kb)
    await member_reset(state)


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
    await cb.message.delete()
    data = await state.get_data()
    not_done_tasks = '\n'.join(data['not_done_tasks_list'])
    report_id = data['rep'][0]
    await sqlite_db.update_report_not_done_tasks(report_id, not_done_tasks)

    await update_report_message(report_id)

    await cb.message.answer('<b>Не выполненные задания</b> успешно изменены',
                            reply_markup=kb.member_menu_kb)
    await member_reset(state)


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
    await cb.message.delete()
    data = await state.get_data()
    scheduled_tasks = '\n'.join(data['scheduled_tasks_list'])
    report_id = data['rep'][0]
    await sqlite_db.update_report_scheduled_tasks(report_id, scheduled_tasks)

    await update_report_message(report_id)

    await cb.message.answer('<b>Запланированные задания</b> успешно изменены',
                            reply_markup=kb.member_menu_kb)
    await member_reset(state)


@dp.message_handler(text='✅ Закрытые цели', state=SessionRole.member)
async def completed_goals(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    m = await msg.answer('Отправьте ссылку на ноушен:',
                         reply_markup=kb.prev_step_reply_kb)
    await state.update_data(msg=m)
    await Goals.notion_link.set()


@dp.message_handler(state=Goals.notion_link)
async def listening_notion_link(msg: Message, state: FSMContext):
    input_text = msg.text
    if not (input_text.startswith('https://www.notion.so') or input_text.startswith('www.notion.so')):
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.\n'
                         'Ссылка должна начинаться с https://www.notion.so',
                         reply_markup=kb.prev_step_reply_kb)
    else:
        await state.update_data(notion_link=input_text.strip())
        await delete_prev_message(msg.from_id, state)
        m = await msg.answer('💰Введите сумму закрытия в ₽:',
                             reply_markup=kb.prev_step_reply_kb)
        await state.update_data(msg=m)
        await Goals.check_amount.set()


@dp.message_handler(state=Goals.check_amount)
async def listening_check_amount(msg: Message, state: FSMContext):
    try:
        check_amount = int(msg.text)
        await delete_prev_message(msg.from_id, state)
        m = await msg.answer('📷 Прикрепите видео или фото, относящееся к цели:',
                             reply_markup=kb.prev_step_reply_kb)
        await state.update_data(msg=m, check_amount=check_amount)
        await Goals.media.set()
    except ValueError:
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.',
                         reply_markup=kb.prev_step_reply_kb)


@dp.message_handler(state=Goals.media, content_types=['video', 'photo'])
async def listening_video(msg: Message, state: FSMContext):
    await msg.delete()
    await delete_prev_message(msg.from_id, state)

    if msg.photo:
        await state.update_data(file_photo=msg.photo[0].file_id)
    elif msg.video:
        await state.update_data(file_video=msg.video.file_id)

    m = await msg.answer('💬 Укажите комментарий:',
                         reply_markup=kb.prev_step_reply_kb)
    await state.update_data(msg=m)
    await Goals.comment.set()


@dp.message_handler(state=Goals.comment)
async def listening_comment(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    data = await state.get_data()
    user_id = await sqlite_db.get_user_id(msg.from_id)
    user = await sqlite_db.get_user_by_id(user_id)
    surname = user[5]
    first_name = user[4]
    user_name = user[3]
    user_status = user[7]
    user_output = f"{get_status_icon(user_status)} {hlink(f'{first_name} {surname}', f'https://t.me/{user_name}')} — {user_status}"
    caption = f"{user_output}\n\n" \
              f"<b>Notion:</b>\n{data['notion_link']}\n\n" \
              f"💰<b>Сумма закрытия:</b> {data['check_amount']}\n\n" \
              f"💬 <b>Комментарий:</b>\n- {msg.text}"

    if 'file_photo' in data:
        await bot.send_photo(chat_id=CONFIG['channels']['goals_channel'],
                             photo=data['file_photo'],
                             caption=caption)
    elif 'file_video' in data:
        await bot.send_video(chat_id=CONFIG['channels']['goals_channel'],
                             video=data['file_video'],
                             caption=caption)

    m = await msg.answer('Отчёт о выполненной цели добавлен ✅',
                         reply_markup=kb.member_menu_kb)
    await member_reset(state)
    await state.update_data(msg=m)
