import asyncio
import os
import re

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.markdown import hlink

from dispatcher import dp, bot
from google.google_manager import upload_file_to_google_drive
from keyboards import keyboards as kb
from utils.reports import (
    print_report, update_selected_done_tasks
)
from utils.request import (
    request_to_user, request_from_user, commit_request, print_request, update_request_message,
    update_req_recipients_points, update_request_hashtags
)
from utils.utils import (
    format_recipients, format_addressers, commit_report, delete_prev_message, get_status_icon, distribute_points
)
from states import SessionRole, CreateRequest, CreateReport, UserEdition, EditRequest, EditReport, Goals
from datetime import datetime, time

from utils.validators import validate_date
from data import sqlite_db
from data import config as cfg


async def member_start(msg: Message, state: FSMContext):
    m = await msg.answer(text='Главное меню:',
                         reply_markup=kb.member_menu_kb)
    await state.reset_data()
    await state.update_data(msg=m)
    await SessionRole.member.set()


@dp.message_handler(text='↩️ Вернуться назад', state=[SessionRole.member, CreateRequest.text,
                                                      CreateRequest.date, CreateReport.earned,
                                                      EditRequest.date, EditRequest.text,
                                                      EditRequest.status, EditReport.earned,
                                                      Goals.days, Goals.media, Goals.check_amount,
                                                      Goals.notion_link, Goals.comment,
                                                      EditRequest.attach_file,
                                                      EditRequest.attach_file])
async def back_to_member_menu_kb(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    await member_start(msg, state)


@dp.callback_query_handler(text='prev_step', state=[SessionRole.member, EditRequest.select_member_request,
                                                    EditRequest.select_request_headers,
                                                    EditRequest.date, EditRequest.status,
                                                    EditRequest.addressers, EditRequest.recipients,
                                                    EditRequest.add_hashtags, CreateRequest.request_from,
                                                    CreateRequest.request_to, CreateRequest.date,
                                                    CreateReport.list_of_done_tasks,
                                                    CreateReport.list_of_not_done_tasks,
                                                    CreateReport.list_of_scheduled_tasks,
                                                    EditReport.list_of_done_tasks,
                                                    EditReport.list_of_not_done_tasks,
                                                    EditReport.list_of_scheduled_tasks,
                                                    EditReport.select_report_headers,
                                                    EditReport.select_member_report, EditRequest.attach_file
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
    users = [user for user in users if user[1] not in cfg.CONFIG['hidden_users']]
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
        (users[user_index][1], users[user_index][4], users[user_index][5], users[user_index][7],)
        for user_index in data['request_from']
    ]
    main_recipient = users[data['main_recipient']]
    main_recipient = (main_recipient[1], main_recipient[4], main_recipient[5], main_recipient[7],)
    if data['secondary_recipient'] is not None:
        secondary_recipient = users[data['secondary_recipient']]
        secondary_recipient = (
            secondary_recipient[1], secondary_recipient[4], secondary_recipient[5], secondary_recipient[7],
        )
    else:
        secondary_recipient = ()
    output = print_request(request_id=request_id,
                           status=cfg.REQUEST_STATUS['in_progress'],
                           addressers=addressers,
                           main_recipient=main_recipient,
                           secondary_recipient=secondary_recipient,
                           text=data['text'],
                           date=data['date'])
    await cb.message.answer(output,
                            reply_markup=kb.member_menu_kb)
    await cb.message.delete()
    msg = await bot.send_message(chat_id=cfg.CONFIG['channels']['request_channel'],
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
            users = [user for user in users if user[1] not in cfg.CONFIG['hidden_users']]
            await state.update_data(curr_users=users)
            await cb.message.answer(f'{(await format_addressers(users))}',
                                    reply_markup=(await kb.update_addressers_kb(users)))
            await EditRequest.addressers.set()
        case 2:
            users = await sqlite_db.get_users()
            users = [user for user in users if user[1] not in cfg.CONFIG['hidden_users']]
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

    if status == 2 and request_status != 2:
        await cb.message.answer('Загрузите <b>видео</b> 📺 с зума или прикрепите иной <b>файл</b> 📄:',
                                reply_markup=kb.edit_request_status_kb)
        await EditRequest.attach_file.set()
        return

    if status != 2 and request_status == 2:
        await update_req_recipients_points(curr_request, '-')

    await sqlite_db.update_request_status(request_id, status)
    await update_request_message(request_id)

    await cb.message.answer('Статус запроса успешно обновлён',
                            reply_markup=kb.member_menu_kb)
    await member_reset(state)


@dp.callback_query_handler(text='skip', state=EditRequest.attach_file)
async def skip_attaching_file(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr_request = data['req']
    request_id = curr_request[0]
    await sqlite_db.update_request_status(request_id, 2)
    await update_request_message(request_id)
    await update_req_recipients_points(data['req'], '+')

    await cb.message.answer('Статус запроса успешно обновлён ✅',
                            reply_markup=kb.member_menu_kb)
    await cb.message.delete()
    await member_reset(state)


@dp.message_handler(state=EditRequest.attach_file, content_types=['video', 'document'])
async def listen_request_video(msg: Message, state: FSMContext):
    if msg.video:
        file_content = msg.video
    elif msg.document:
        file_content = msg.document
    else:
        await msg.answer('Недопустимый тип файла.',
                         reply_markup=kb.member_menu_kb)
        await member_reset(state)
        return

    m = await msg.answer('Подождите, идёт загрузка...')
    file = await bot.get_file(file_content.file_id)
    file_extension = file_content.file_name.split('.')[-1]
    file_path = f"temp/file.{file_extension}"
    await bot.download_file(file.file_path, file_path)

    user = await sqlite_db.get_user_by_id(await sqlite_db.get_user_id(msg.from_id))

    data = await state.get_data()
    curr_request = data['req']
    request_id = curr_request[0]
    file_name = f"{msg.from_id}_{'video' if msg.video else 'document'}_{request_id}.{file_extension}"

    video_shared_link = upload_file_to_google_drive(user, file_name, file_path)

    os.remove(file_path)

    await m.delete()
    message_text = 'Добавьте подходящие хештеги:'
    await state.update_data(message_text=message_text,
                            video_shared_link=video_shared_link,
                            request_id=request_id)
    await msg.answer(message_text,
                     reply_markup=kb.hashtag_kb())
    await EditRequest.add_hashtags.set()
    await msg.delete()


@dp.callback_query_handler(Text(startswith="task_"), state=EditRequest.add_hashtags)
async def add_hashtags(cb: CallbackQuery, state: FSMContext):
    await update_request_hashtags(cb, state)


@dp.callback_query_handler(text='next_step', state=EditRequest.add_hashtags)
async def finish_status_edition(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'hashtag_indices' not in data or not len(data['hashtag_indices']):
        m = await cb.message.answer('Необходимо выбрать хотя бы один хештег.')
        await asyncio.sleep(2)
        await m.delete()
    else:
        hashtag_indices = data['hashtag_indices']
        await sqlite_db.update_request_status(data['request_id'], 2)
        await update_request_message(data['request_id'], data['video_shared_link'], hashtag_indices)
        await update_req_recipients_points(data['req'], '+')

        await cb.message.answer('Статус запроса успешно обновлён ✅',
                                reply_markup=kb.member_menu_kb)
        await cb.message.delete()
        await member_reset(state)


@dp.callback_query_handler(Text(startswith='user_'), state=EditRequest.addressers)
async def edit_addressers(cb: CallbackQuery, state: FSMContext):
    await request_from_user(cb, state)


@dp.callback_query_handler(text='next_step', state=EditRequest.addressers)
async def confirm_edit_addressers(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = data['curr_users']
    request_id = data['req'][0]
    addressers = '\n'.join([str(users[user_index][1]) for user_index in data['request_from']])
    await sqlite_db.update_request_addressers(request_id, addressers)

    await update_request_message(request_id)

    await cb.message.answer('Отправители запроса успешно изменены ✅',
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
        main_recipient = str(users[data['main_recipient']][1])
        if data['secondary_recipient'] is not None:
            secondary_recipient = str(users[data['secondary_recipient']][3])
        else:
            secondary_recipient = ''
        await sqlite_db.update_request_recipients(request_id, main_recipient, secondary_recipient)
        await update_request_message(request_id)
        await cb.message.answer('Получатели успешно изменены ✅',
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
async def add_earned(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    report_time = cfg.get()['report_time']
    left_time_parts = report_time['start'].split(':')
    left_time = time(hour=int(left_time_parts[0]), minute=int(left_time_parts[1]))
    right_time_parts = report_time['end'].split(':')
    right_time = time(hour=int(right_time_parts[0]), minute=int(right_time_parts[1]))

    if left_time <= datetime.now().time() < right_time:
        m = await msg.answer('Сколько заработали 💰₽ за сегодняшний день?\n'
                             'Введите значение в следующем формате: 150000',
                             reply_markup=kb.prev_step_reply_kb)
        await state.update_data(msg=m)
        await CreateReport.earned.set()
    else:
        await msg.answer(f'Отчёт можно заполнить только в период с {report_time["start"]} до {report_time["end"]}.',
                         reply_markup=kb.member_menu_kb)
        await member_reset(state)


@dp.message_handler(state=CreateReport.earned)
async def enter_done_tasks(msg: Message, state: FSMContext):
    try:
        result = int(msg.text)
        await delete_prev_message(msg.from_id, state)

        user_id = await sqlite_db.get_user_id(msg.from_id)
        user_scheduled_tasks = await sqlite_db.get_user_scheduled_tasks(user_id)
        if len(user_scheduled_tasks):
            await state.update_data(earned=result, user_id=msg.from_id, curr_tasks=user_scheduled_tasks,
                                    done_tasks_indices=[])
            await msg.answer('✅ Выберите задачи, которые сегодня выполнили:\n'
                             '(Не помеченные задачи автоматически будут иметь статус не выполненных)',
                             reply_markup=kb.scheduled_tasks_kb(user_scheduled_tasks))
            await CreateReport.list_of_done_tasks.set()
        else:
            message = await msg.answer('📝 Введите список запланированных на завтра задач:\n'
                                       '(Отправьте задачи по одной, а в конце нажмите "Подтвердить")',
                                       reply_markup=kb.apply_tasks_kb())
            await state.update_data(msg_id=message.message_id, user_id=msg.from_id, earned=result,
                                    new_scheduled_tasks=[])
            await CreateReport.list_of_scheduled_tasks.set()
    except ValueError:
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.')


@dp.callback_query_handler(Text(startswith='task_'), state=CreateReport.list_of_done_tasks)
async def select_done_tasks(cb: CallbackQuery, state: FSMContext):
    await update_selected_done_tasks(cb, state, '✅ Выберите задачи, которые сегодня выполнили:\n'
                                                '(Не помеченные задачи автоматически будут иметь статус не выполненных)')


@dp.callback_query_handler(text='next_step', state=CreateReport.list_of_done_tasks)
async def enter_scheduled_tasks(cb: CallbackQuery, state: FSMContext):
    await cb.message.delete()
    data = await state.get_data()
    curr_tasks = data['curr_tasks']
    done_tasks_indices = data['done_tasks_indices']

    done_tasks = []
    not_done_tasks = []
    for i in range(len(curr_tasks)):
        if i in done_tasks_indices:
            done_tasks.append(curr_tasks[i])
        else:
            not_done_tasks.append(curr_tasks[i])

    if len(done_tasks):
        await state.update_data(done_tasks=done_tasks)
    if len(not_done_tasks):
        await state.update_data(not_done_tasks=not_done_tasks)

    message = await cb.message.answer('📝 Введите список запланированных на завтра задач:\n'
                                      '(Отправьте задачи по одной, а в конце нажмите "Подтвердить")',
                                      reply_markup=kb.apply_tasks_kb())
    await state.update_data(msg_id=message.message_id,
                            new_scheduled_tasks=[])
    await CreateReport.list_of_scheduled_tasks.set()


@dp.message_handler(state=CreateReport.list_of_scheduled_tasks)
async def listening_scheduled_tasks(msg: Message, state: FSMContext):
    await msg.delete()
    data = await state.get_data()
    scheduled_tasks_list = data['new_scheduled_tasks']
    scheduled_tasks_list.append(msg.text)
    await state.update_data(new_scheduled_tasks=scheduled_tasks_list)
    data = await state.get_data()
    append_text = '\n'.join(['- ' + task for task in data['new_scheduled_tasks']])
    await bot.edit_message_text(text='📝 Введите список запланированных на завтра задач:\n'
                                     '(Отправьте задачи по одной, а в конце нажмите "Подтвердить")\n\n'
                                     f'{append_text}',
                                chat_id=msg.from_id,
                                message_id=data['msg_id'],
                                reply_markup=kb.apply_tasks_kb())


@dp.callback_query_handler(text='apply_tasks', state=CreateReport.list_of_scheduled_tasks)
async def apply_scheduled_tasks(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_scheduled_tasks = data['new_scheduled_tasks']

    if len(new_scheduled_tasks):
        await cb.message.delete()
        await commit_report(data)

        author_id = await sqlite_db.get_user_id(cb.from_user.id)
        report_id = (await sqlite_db.get_user_last_report_id(author_id))[0]
        user = await sqlite_db.get_user_by_id(author_id)
        surname = user[5]
        first_name = user[4]
        telegram_id = user[1]
        user_status = user[7]
        earned = data['earned']

        user = (telegram_id, first_name, surname, user_status,)

        done_tasks_descriptions = None
        if 'done_tasks' in data:
            done_tasks = data['done_tasks']
            done_tasks_descriptions = [task[2] for task in done_tasks]

        not_done_tasks_descriptions = None
        if 'not_done_tasks' in data:
            not_done_tasks = data['not_done_tasks']
            not_done_tasks_descriptions = [task[2] for task in not_done_tasks]

        output = await print_report(report_id=report_id,
                                    user=user,
                                    earned=earned,
                                    scheduled_tasks=new_scheduled_tasks,
                                    done_tasks=done_tasks_descriptions,
                                    not_done_tasks=not_done_tasks_descriptions)

        await cb.message.answer(output, reply_markup=kb.member_menu_kb)
        msg = await bot.send_message(chat_id=cfg.CONFIG['channels']['report_channel'],
                                     text=output)
        await sqlite_db.add_message_id_to_report(report_id, msg.message_id)

        await member_reset(state)
    else:
        m = await cb.message.answer('Необходимо ввести хотя бы одну задачу.')
        await asyncio.sleep(2)
        await m.delete()


# @dp.message_handler(text='✏️ Ред. отчётность', state=SessionRole.member)
# async def edit_user_report(msg: Message, state: FSMContext):
#     await delete_prev_message(msg.from_id, state)
#     user_id = await sqlite_db.get_user_id(msg.from_id)
#     await state.update_data(role_state=(await state.get_state()).split(':')[1])
#     reports = await sqlite_db.get_user_reports(user_id)
#     if len(reports):
#         await state.update_data(user_id=user_id, reps=reports)
#         await msg.answer('Выберите отчёт для редактирования:',
#                          reply_markup=(await kb.member_reports_kb(reports)))
#         await EditReport.select_member_report.set()
#     else:
#         await msg.answer('Этот участник еще не создал ни одного отчёта.',
#                          reply_markup=kb.prev_step_reply_kb)
#
#
# @dp.callback_query_handler(Text(startswith='elm_'), state=EditReport.select_member_report)
# async def select_member_report(cb: CallbackQuery, state: FSMContext):
#     await cb.message.delete()
#     rep_index = int(cb.data[4:])
#     await state.update_data(rep=(await state.get_data())['reps'][rep_index])
#     await cb.message.answer('Выберите поле отчёта, которое хотите отредактировать:',
#                             reply_markup=(await kb.report_headers_kb()))
#     await EditReport.select_report_headers.set()
#
#
# @dp.callback_query_handler(Text(startswith='elm_'), state=EditReport.select_report_headers)
# async def select_report_headers(cb: CallbackQuery, state: FSMContext):
#     header_index = int(cb.data[4:])
#     await cb.message.delete()
#     match header_index:
#         case 0:
#             m = await cb.message.answer('Сколько заработали 💰₽ за сегодняшний день?\n'
#                                         'Введите значение в следующем формате: 150000',
#                                         reply_markup=kb.prev_step_reply_kb)
#             await state.update_data(msg=m)
#             await EditReport.earned.set()
#         case 1:
#             message = await cb.message.answer('✅ Введите список выполненных сегодня задач (по одной):',
#                                               reply_markup=kb.apply_tasks_kb())
#             await state.update_data(done_tasks_list=[], message_id=message.message_id)
#             await EditReport.list_of_done_tasks.set()
#         case 2:
#             message = await cb.message.answer('❌ Введите список не выполненных сегодня задач (по одной):',
#                                               reply_markup=kb.apply_tasks_kb())
#             await state.update_data(not_done_tasks_list=[], message_id=message.message_id)
#             await EditReport.list_of_not_done_tasks.set()
#         case 3:
#             message = await cb.message.answer('📝 Введите список запланированных на завтра задач (по одной):',
#                                               reply_markup=kb.apply_tasks_kb())
#             await state.update_data(scheduled_tasks_list=[], message_id=message.message_id)
#             await EditReport.list_of_scheduled_tasks.set()
#
#
# @dp.message_handler(state=EditReport.earned)
# async def edit_phone_time(msg: Message, state: FSMContext):
#     try:
#         result = int(msg.text)
#         await delete_prev_message(msg.from_id, state)
#         data = await state.get_data()
#         report = data['rep']
#         report_id = report[0]
#         await sqlite_db.update_report_earned(report_id, result)
#
#         await update_report_message(report_id)
#
#         await msg.answer('<b>Заработанная сумма</b> успешно изменена',
#                          reply_markup=kb.member_menu_kb)
#         await member_reset(state)
#
#     except ValueError:
#         await msg.answer('Неверный формат ввода. Попробуйте еще раз.')
#
#
# @dp.message_handler(state=EditReport.list_of_done_tasks)
# async def edit_list_of_done_tasks(msg: Message, state: FSMContext):
#     data = await state.get_data()
#     done_tasks_list = data['done_tasks_list']
#     done_tasks_list.append(msg.text)
#     await state.update_data(done_tasks_list=done_tasks_list)
#     append_text = '\n'.join(['- ' + task for task in data['done_tasks_list']])
#     await bot.edit_message_text(text=f"✅ Введите список выполненных сегодня задач (по одной):\n\n"
#                                      f"{append_text}",
#                                 chat_id=msg.from_id,
#                                 message_id=data['message_id'],
#                                 reply_markup=kb.apply_tasks_kb())
#
#
# @dp.callback_query_handler(text='apply_tasks', state=EditReport.list_of_done_tasks)
# async def apply_edition_done_tasks(cb: CallbackQuery, state: FSMContext):
#     await cb.message.delete()
#     data = await state.get_data()
#     done_tasks = '\n'.join(data['done_tasks_list'])
#     report_id = data['rep'][0]
#     await sqlite_db.update_report_done_tasks(report_id, done_tasks)
#
#     await update_report_message(report_id)
#
#     await cb.message.answer('Выполненные задания успешно изменены',
#                             reply_markup=kb.member_menu_kb)
#     await member_reset(state)
#
#
# @dp.message_handler(state=EditReport.list_of_not_done_tasks)
# async def edit_list_of_not_done_tasks(msg: Message, state: FSMContext):
#     data = await state.get_data()
#     not_done_tasks_list = data['not_done_tasks_list']
#     not_done_tasks_list.append(msg.text)
#     await state.update_data(not_done_tasks_list=not_done_tasks_list)
#     append_text = '\n'.join(['- ' + task for task in data['not_done_tasks_list']])
#     await bot.edit_message_text(text=f"❌ Введите список не выполненных сегодня задач (по одной):\n\n"
#                                      f"{append_text}",
#                                 chat_id=msg.from_id,
#                                 message_id=data['message_id'],
#                                 reply_markup=kb.apply_tasks_kb())
#
#
# @dp.callback_query_handler(text='apply_tasks', state=EditReport.list_of_not_done_tasks)
# async def apply_edition_not_done_tasks(cb: CallbackQuery, state: FSMContext):
#     await cb.message.delete()
#     data = await state.get_data()
#     not_done_tasks = '\n'.join(data['not_done_tasks_list'])
#     report_id = data['rep'][0]
#     await sqlite_db.update_report_not_done_tasks(report_id, not_done_tasks)
#
#     await update_report_message(report_id)
#
#     await cb.message.answer('<b>Не выполненные задания</b> успешно изменены',
#                             reply_markup=kb.member_menu_kb)
#     await member_reset(state)
#
#
# @dp.message_handler(state=EditReport.list_of_scheduled_tasks)
# async def edit_list_of_scheduled_tasks(msg: Message, state: FSMContext):
#     data = await state.get_data()
#     scheduled_tasks = data['scheduled_tasks_list']
#     scheduled_tasks.append(msg.text)
#     await state.update_data(scheduled_tasks_list=scheduled_tasks)
#     append_text = '\n'.join(['- ' + task for task in data['scheduled_tasks_list']])
#     await bot.edit_message_text(text=f"📝 Введите список запланированных на завтра задач (по одной):\n\n"
#                                      f"{append_text}",
#                                 chat_id=msg.from_id,
#                                 message_id=data['message_id'],
#                                 reply_markup=kb.apply_tasks_kb())
#
#
# @dp.callback_query_handler(text='apply_tasks', state=EditReport.list_of_scheduled_tasks)
# async def apply_edition_scheduled_tasks(cb: CallbackQuery, state: FSMContext):
#     await cb.message.delete()
#     data = await state.get_data()
#     scheduled_tasks = '\n'.join(data['scheduled_tasks_list'])
#     report_id = data['rep'][0]
#     await sqlite_db.update_report_scheduled_tasks(report_id, scheduled_tasks)
#
#     await update_report_message(report_id)
#
#     await cb.message.answer('<b>Запланированные задания</b> успешно изменены',
#                             reply_markup=kb.member_menu_kb)
#     await member_reset(state)


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
    telegram_id = user[1]
    user_status = user[7]
    user_output = f"{hlink(f'{first_name} {surname}', f'tg://user?id={telegram_id}')} — {get_status_icon(user_status)} {user_status}"
    caption = f"{user_output}\n\n" \
              f"<b>Notion:</b>\n{data['notion_link']}\n\n" \
              f"💰<b>Сумма закрытия:</b> {data['check_amount']}\n\n" \
              f"💬 <b>Комментарий:</b>\n- {msg.text}"

    if 'file_photo' in data:
        await bot.send_photo(chat_id=cfg.CONFIG['channels']['goals_channel'],
                             photo=data['file_photo'],
                             caption=caption)
    elif 'file_video' in data:
        await bot.send_video(chat_id=cfg.CONFIG['channels']['goals_channel'],
                             video=data['file_video'],
                             caption=caption)
    user_id = await sqlite_db.get_user_id(msg.from_id)

    check_amount = data['check_amount']
    await distribute_points(user_id, check_amount)
    await sqlite_db.add_goal(user_id, data['notion_link'], check_amount, msg.text)

    m = await msg.answer('Отчёт о выполненной цели добавлен ✅',
                         reply_markup=kb.member_menu_kb)
    await member_reset(state)
    await state.update_data(msg=m)


