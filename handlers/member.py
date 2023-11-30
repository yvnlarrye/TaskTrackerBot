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
from google.drive_manager import *
from keyboards import keyboards as kb
from utils.reports import (
    print_report, update_selected_done_tasks, format_report_data_for_table
)
from utils.request import (
    request_to_user, request_from_user, commit_request, print_request, update_request_message,
    update_req_recipients_points, update_request_hashtags, format_request_data_for_table
)
from utils.utils import (
    format_recipients, format_addressers, commit_report, delete_prev_message, get_status_icon, distribute_points,
    format_goal_data_for_table, format_points_data_for_table
)
from states import SessionRole, CreateRequest, CreateReport, UserEdition, EditRequest, EditReport, Goals
from datetime import datetime, time, date
from utils.validators import validate_date
from data import sqlite_db, config as cfg
from google.sheet_manager import append_row_in_table


async def member_start(msg: Message, state: FSMContext):
    m = await msg.answer(text='Главное меню:', reply_markup=kb.member_menu_kb)
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
                                                    EditReport.select_member_report, EditRequest.attach_file,
                                                    CreateReport.earned, CreateReport.screenshots
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
async def create_request(msg: Message, state: FSMContext):
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
        req_date = re.sub(r"[/\\-]", ".", re.search(r"(\d+.*?\d+.*?\d+)", msg.text).group(1))
        await validate_date(req_date, msg)
        await state.update_data(date=req_date)

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
    last_req_serial_number = await sqlite_db.get_last_request_serial_number()
    serial_number = last_req_serial_number + 1
    await state.update_data(serial_number=serial_number, author_telegram_id=cb.from_user.id)
    author = await sqlite_db.get_user_by_id(await sqlite_db.get_user_id(cb.from_user.id))
    data = await state.get_data()
    await commit_request(data)
    author_id = await sqlite_db.get_user_id(cb.from_user.id)
    request_id = await sqlite_db.get_user_last_request_id(author_id)

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
    output = print_request(serial_number=serial_number,
                           status=cfg.REQUEST_STATUS['in_progress'],
                           addressers=addressers,
                           main_recipient=main_recipient,
                           secondary_recipient=secondary_recipient,
                           text=data['text'],
                           date=data['date'])

    row_data = await format_request_data_for_table(request_id=request_id,
                                                   author=author,
                                                   serial_number=serial_number)
    append_row_in_table(table_name=cfg.CONFIG['request_sheet_name'], row_range='A:L', values=[row_data])

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
        m = await cb.message.answer(
            f'Отправь ссылку на <b>видео</b> 📺 с записью зума c Google диска или YouTube. Или загрузи сюда любой <b>файл</b> 📄 до 20 мб.\n\n'
            f'Не знаешь как залить видео на Google диск или YouTube и поделиться рабочей ссылкой? Смотри!\n'
            f'{hlink("Как загрузить видео на YouTube и поделиться", "https://drive.google.com/file/d/1e-qGRUUFCGDAxJruULwxEz6O8AvTWIdl/view?usp=drive_link")}\n'
            f'{hlink("Как загрузить видео на Google Disk и поделиться", "https://drive.google.com/file/d/1B5rZBA565B85ocj2x3Q3LQVQL6s5KPPi/view")}',
            reply_markup=kb.edit_request_status_kb)
        await state.update_data(msg=m)
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


@dp.message_handler(state=EditRequest.attach_file, content_types=['video', 'document', 'text'])
async def listen_request_content(msg: Message, state: FSMContext):
    await msg.delete()
    file_content = None
    video_shared_link = None

    data = await state.get_data()
    curr_request = data['req']
    request_id = curr_request[0]
    serial_number = curr_request[10]

    if msg.text:
        if msg.text.startswith("https://"):
            video_shared_link = msg.text
        else:
            err_msg = await msg.answer("Неверный формат ссылки.")
            await asyncio.sleep(2)
            await err_msg.delete()
            return
    elif msg.video:
        file_content = msg.video
    elif msg.document:
        file_content = msg.document
    else:
        await msg.answer('Недопустимый формат.',
                         reply_markup=kb.member_menu_kb)
        await member_reset(state)
        return

    if file_content:
        m = await msg.answer('Подождите, идёт загрузка...')
        file_id = file_content.file_id
        file = await bot.get_file(file_id)
        file_extension = file_content.file_name.split('.')[-1]
        file_path = f"temp/{file_id}.{file_extension}"
        try:
            await bot.download_file(file.file_path, file_path)
            user = await sqlite_db.get_user_by_id(await sqlite_db.get_user_id(msg.from_id))
            file_name = f"{msg.from_id}_{'video' if msg.video else 'document'}_{serial_number}.{file_extension}"
            video_shared_link = upload_content(user, file_name, file_path, cfg.CONFIG['video_folder_id'])
            os.remove(file_path)
        except Exception as e:
            print(e)
            err_msg = await msg.answer("Файл слишком большой, попробуйте другой способ.")
            await asyncio.sleep(2)
            await err_msg.delete()
            return
        await m.delete()

    await delete_prev_message(msg.from_id, state)

    message_text = 'Добавьте подходящие хештеги:'
    await state.update_data(message_text=message_text,
                            video_shared_link=video_shared_link,
                            request_id=request_id)
    await msg.answer(message_text,
                     reply_markup=kb.hashtag_kb())
    await EditRequest.add_hashtags.set()


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
            secondary_recipient = str(users[data['secondary_recipient']][1])
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
        req_date = re.sub(r"[/\\-]", ".", re.search(r"(\d+.*?\d+.*?\d+)", msg.text).group(1))
        await validate_date(req_date, msg)
        data = await state.get_data()
        request_id = data['req'][0]
        await sqlite_db.update_request_date(request_id, req_date)
        await update_request_message(request_id)

        await msg.answer('Срок успешно изменен.',
                         reply_markup=kb.member_menu_kb)
        await member_reset(state)
    except AttributeError:
        req_date = datetime.now().strftime('%d.%m.%y')
        await msg.answer(text='Неверный формат даты',
                         reply_markup=kb.prev_step_reply_kb)
        await msg.answer(f'Введите дату срока запроса в формате:\n'
                         f'DD.MM.YY\n'
                         f'Например: {req_date}')


@dp.message_handler(text='📩 Отчетность', state=SessionRole.member)
async def add_earned(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    report_time = cfg.get()['report_time']
    time_restriction = cfg.get()['time_restriction']
    left_time_parts = report_time['start'].split(':')
    left_time = time(hour=int(left_time_parts[0]), minute=int(left_time_parts[1]))
    right_time_parts = report_time['end'].split(':')
    right_time = time(hour=int(right_time_parts[0]), minute=int(right_time_parts[1]))

    if (left_time <= datetime.now().time() < right_time) or not time_restriction:
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
async def enter_screenshots(msg: Message, state: FSMContext):
    try:
        result = int(msg.text)
        await msg.delete()
        await delete_prev_message(msg.from_id, state)
        await state.update_data(earned=result, photos=[])
        if result == 0:
            await done_tasks_f(msg, state)
        else:
            message = await msg.answer(
                text=f'Добавьте скриншоты дохода: скрин поступления из мобильного приложения или фото наличных денежных средств.\n\n'
                     f'(Отправьте фото по одному, а в конце нажмите «Подтвердить»)\n',
                reply_markup=kb.apply_tasks_kb())
            await state.update_data(msg_id=message.message_id)
            await CreateReport.screenshots.set()
    except ValueError:
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.')


@dp.message_handler(content_types=['photo'], state=CreateReport.screenshots)
async def listen_screenshots(msg: Message, state: FSMContext):
    if msg.photo:
        await msg.delete()
        data = await state.get_data()
        photos = data['photos']
        photo_id = msg.photo[-1].file_id
        file_info = await bot.get_file(photo_id)
        file_extension = file_info.file_path.split('photos/')[1].split('.')[1]
        file_name = f'{photo_id}.{file_extension}'
        await msg.photo[-1].download(destination_file=f'temp/{file_name}')
        photos.append(file_name)
        append_text = '\n'.join([f'- photo_{i + 1}' for i, photo in enumerate(photos)])
        await bot.edit_message_text(
            text=f'Добавьте скриншоты дохода: скрин поступления из мобильного приложения или фото наличных денежных средств.\n\n'
                 f'(Отправьте фото по одному, а в конце нажмите «Подтвердить»)\n'
                 f'{append_text}',
            chat_id=msg.from_id,
            message_id=data['msg_id'],
            reply_markup=kb.apply_tasks_kb())
        await state.update_data(photos=photos)


@dp.callback_query_handler(text='apply_tasks', state=CreateReport.screenshots)
async def enter_done_tasks(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photo_files = data['photos']
    if len(photo_files):
        await done_tasks_f(cb.message, state)
    else:
        m = await cb.message.answer('Необходимо загрузить хотя бы один скриншот.')
        await asyncio.sleep(2)
        await m.delete()


async def done_tasks_f(msg: Message, state: FSMContext):
    try:
        await msg.delete()
    except:
        pass
    user_id = await sqlite_db.get_user_id(msg.chat.id)
    user_scheduled_tasks = await sqlite_db.get_user_scheduled_tasks(user_id)
    if len(user_scheduled_tasks):
        await state.update_data(user_id=msg.chat.id, curr_tasks=user_scheduled_tasks,
                                done_tasks_indices=[])
        await msg.answer('✅ Выберите задачи, которые сегодня выполнили:\n'
                         '(Не помеченные задачи автоматически будут иметь статус не выполненных)',
                         reply_markup=kb.scheduled_tasks_kb(user_scheduled_tasks))
        await CreateReport.list_of_done_tasks.set()
    else:
        message = await msg.answer('📝 Введите список запланированных на завтра задач:\n'
                                   '(Отправьте задачи по одной, а в конце нажмите "Подтвердить")',
                                   reply_markup=kb.apply_tasks_kb())
        await state.update_data(msg_id=message.message_id, user_id=msg.chat.id,
                                new_scheduled_tasks=[])
        await CreateReport.list_of_scheduled_tasks.set()


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
        report_id = await sqlite_db.get_user_last_report_id(author_id)
        user = await sqlite_db.get_user_by_id(author_id)
        surname = user[5]
        first_name = user[4]
        telegram_id = user[1]
        user_status = user[7]
        earned = data['earned']

        user_transfer = (telegram_id, first_name, surname, user_status,)

        done_tasks_descriptions = None
        if 'done_tasks' in data:
            done_tasks = data['done_tasks']
            done_tasks_descriptions = [task[2] for task in done_tasks]

        not_done_tasks_descriptions = None
        if 'not_done_tasks' in data:
            not_done_tasks = data['not_done_tasks']
            not_done_tasks_descriptions = [task[2] for task in not_done_tasks]

        output = await print_report(report_id=report_id,
                                    user=user_transfer,
                                    earned=earned,
                                    scheduled_tasks=new_scheduled_tasks,
                                    done_tasks=done_tasks_descriptions,
                                    not_done_tasks=not_done_tasks_descriptions)

        photo_files = data['photos']

        folder_link = None
        for i, file in enumerate(photo_files):
            file_loc = f'temp/{file}'
            curr_date = date.today().strftime("%d.%m.%Y")
            file_extension = file.split('.')[1]
            file_name = f'{report_id}_{first_name}_{surname}_{curr_date}_{i + 1}.{file_extension}'
            folder_link = upload_report_photo(user=user,
                                              file_name=file_name,
                                              file_loc=file_loc,
                                              root_folder_id=cfg.CONFIG['screenshots_folder_id'], )
            os.remove(file_loc)

        await cb.message.answer(output, reply_markup=kb.member_menu_kb)
        msg = await bot.send_message(chat_id=cfg.CONFIG['channels']['report_channel'],
                                     text=output)
        await sqlite_db.add_message_id_to_report(report_id, msg.message_id)
        row_data = await format_report_data_for_table(report_id=report_id, author=user, folder_link=folder_link)
        append_row_in_table(table_name=cfg.CONFIG['report_sheet_name'], row_range='A:K', values=[row_data])
        await member_reset(state)
    else:
        m = await cb.message.answer('Необходимо ввести хотя бы одну задачу.')
        await asyncio.sleep(2)
        await m.delete()


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
    if not input_text.startswith('https://'):
        await msg.answer('Неверный формат ввода. Попробуйте еще раз.\n'
                         'Ссылка должна начинаться с https://',
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
        await state.update_data(file_photo=msg.photo[-1].file_id)
    elif msg.video:
        await state.update_data(file_video={
            'video_id': msg.video.file_id,
            'video_name': msg.video.file_name
        })

    m = await msg.answer('💬 Укажите комментарий:',
                         reply_markup=kb.prev_step_reply_kb)
    await state.update_data(msg=m)
    await Goals.comment.set()


@dp.message_handler(state=Goals.comment, content_types=['text'])
async def listening_comment(msg: Message, state: FSMContext):
    await delete_prev_message(msg.from_id, state)
    m = await msg.answer('Подождите, идет загрузка...')
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

    user_id = await sqlite_db.get_user_id(msg.from_id)
    check_amount = data['check_amount']
    await distribute_points(user_id, check_amount)
    await sqlite_db.add_goal(user_id, data['notion_link'], check_amount, msg.text)
    goal_id = await sqlite_db.get_user_last_goal_id(user_id)
    shared_link = None
    if 'file_photo' in data:
        photo_id = data['file_photo']
        file_info = await bot.get_file(photo_id)
        file_extension = file_info.file_path.split('photos/')[1].split('.')[1]
        file_name = f'temp/{photo_id}.{file_extension}'
        await bot.download_file(file_info.file_path, file_name)
        new_file_name = f"{msg.from_id}_photo_{goal_id}.{file_extension}"
        shared_link = upload_content(user, new_file_name, file_name, cfg.CONFIG['goals_content_folder_id'])
        os.remove(file_name)
        await bot.send_photo(chat_id=cfg.CONFIG['channels']['goals_channel'],
                             photo=data['file_photo'],
                             caption=caption)
    elif 'file_video' in data:
        video_id = data['file_video']['video_id']
        video_name = data['file_video']['video_name']

        file_info = await bot.get_file(video_id)
        file_extension = video_name.split('.')[1]
        file_name = f'temp/{video_id}.{file_extension}'
        await bot.download_file(file_info.file_path, file_name)
        new_file_name = f"{msg.from_id}_video_{goal_id}.{file_extension}"
        shared_link = upload_content(user, new_file_name, file_name, cfg.CONFIG['goals_content_folder_id'])
        os.remove(file_name)
        await bot.send_video(chat_id=cfg.CONFIG['channels']['goals_channel'],
                             video=data['file_video']['video_id'],
                             caption=caption)

    row_data = await format_goal_data_for_table(user, shared_link)
    append_row_in_table(table_name=cfg.CONFIG['goal_sheet_name'], row_range='A:I', values=[row_data])
    await m.delete()
    m = await msg.answer('Отчёт о выполненной цели добавлен ✅',
                         reply_markup=kb.member_menu_kb)
    await member_reset(state)
    await state.update_data(msg=m)
