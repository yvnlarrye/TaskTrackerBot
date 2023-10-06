import sqlite3
from dotenv import load_dotenv
import os


async def db_connect() -> None:
    global db, cur
    load_dotenv('.env')
    db_name = str(os.getenv('database_mame'))
    db = sqlite3.connect(db_name)
    cur = db.cursor()
    create_tables()
    db.commit()


def create_tables():
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id          INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
        "telegram_id INTEGER NOT NULL UNIQUE, "
        "role        INTEGER NOT NULL DEFAULT (0), "
        "username    TEXT    UNIQUE,"
        "first_name  TEXT    NOT NULL,"
        "surname     TEXT    NOT NULL,"
        "points      REAL    DEFAULT (0),"
        "status      TEXT    DEFAULT White NOT NULL"
        ")"
    )
    cur.execute(
        'CREATE TABLE IF NOT EXISTS requests ('
        'id         INTEGER  PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,'
        'author_id  INTEGER  REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE NOT NULL,'
        'status     INTEGER  NOT NULL DEFAULT (1),'
        'addressers TEXT     NOT NULL,'
        'main_recipient       TEXT     NOT NULL,'
        'secondary_recipients TEXT,'
        'text       TEXT     NOT NULL,'
        'datetime   DATETIME NOT NULL,'
        'message_id INTEGER  UNIQUE'
        ')'
    )

    cur.execute(
        'CREATE TABLE IF NOT EXISTS reports ('
        'id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, '
        'author_id       INTEGER REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE NOT NULL, '
        'earned          INTEGER NOT NULL DEFAULT (0), '
        'done_tasks      TEXT    NOT NULL, '
        'not_done_tasks  TEXT    NOT NULL, '
        'scheduled_tasks TEXT    NOT NULL, '
        'message_id INTEGER UNIQUE'
        ')'
    )


async def get_user_id(telegram_id: int) -> int:
    """Get user id by telegram id"""
    result = cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    return result.fetchone()[0]


async def get_user_by_id(user_id: int):
    """Gets user by passed id"""
    result = cur.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    )
    return result.fetchone()


async def add_member(telegram_id: int, username: str, first_name: str, surname: str):
    """Adds new user (member)"""
    cur.execute(
        "INSERT INTO users ('telegram_id', 'username', 'first_name', 'surname') VALUES (?, ?, ?, ?)",
        (telegram_id, username, first_name, surname)
    )
    return db.commit()


async def add_admin(telegram_id: int, username: str, first_name: str, surname: str):
    """Adds new admin"""
    cur.execute(
        "INSERT INTO users (telegram_id, role, username, first_name, surname) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, 1, username, first_name, surname)
    )
    return db.commit()


async def get_user_role(user_id: int) -> int:
    """Gets user role"""
    result = cur.execute(
        "SELECT role FROM users WHERE id = ?", (user_id,)
    )
    return int(result.fetchone()[0])


async def update_user_role(user_id: int, role: int):
    cur.execute(
        'UPDATE users SET role = ? WHERE id = ?', (role, user_id,)
    )
    return db.commit()


async def remove_user_by_id(user_id: int):
    """Removes user by passed id"""
    cur.execute("DELETE FROM users WHERE id = ?",
                (user_id,))
    return db.commit()


async def user_exists(telegram_id: int):
    """Checks whether user exists"""
    result = cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    return bool(len(result.fetchall()))


async def get_usernames():
    """Get usernames list"""
    result = cur.execute('SELECT username FROM users')
    return result.fetchall()


async def add_request(author_id: int, status: int, addressers: str, main_recipient: str,
                      secondary_recipients: str, text: str, datetime: str):
    cur.execute(
        "INSERT INTO requests ("
        "author_id, status, addressers, main_recipient, secondary_recipients, text, datetime"
        ") values (?, ?, ?, ?, ?, ?, ?)",
        (author_id, status, addressers, main_recipient, secondary_recipients, text, datetime,)
    )
    db.commit()


async def remove_request_by_id(request_id: int):
    """Removes request by passed id"""
    cur.execute("DELETE FROM requests WHERE id = ?",
                (request_id,))
    return db.commit()


async def get_request_message_id(request_id: int):
    result = cur.execute("SELECT message_id FROM requests WHERE id = ?", (request_id,))
    return result.fetchone()


async def get_request_by_id(request_id: int):
    result = cur.execute(
        "SELECT * FROM requests WHERE id = ?", (request_id,)
    )
    return result.fetchone()


async def get_all_requests():
    result = cur.execute("SELECT * FROM requests")
    return result.fetchall()


async def add_message_id_to_request(request_id, message_id: int):
    cur.execute(
        "UPDATE requests SET message_id = ? WHERE id = ?", (message_id, request_id,)
    )
    db.commit()


async def update_request_status(request_id: int, status: int):
    cur.execute(
        "UPDATE requests SET status = ? WHERE id = ?", (status, request_id,)
    )
    db.commit()


async def update_request_addressers(request_id: int, addressers: str):
    cur.execute(
        "UPDATE requests SET addressers = ? WHERE id = ?", (addressers, request_id,)
    )
    db.commit()


async def update_request_recipients(request_id: int, main_recipient: str, secondary_recipients: str):
    cur.execute(
        "UPDATE requests SET main_recipient = ?, secondary_recipients = ? WHERE id = ?",
        (main_recipient, secondary_recipients, request_id,)
    )
    db.commit()


async def update_request_text(request_id, text: str):
    cur.execute(
        "UPDATE requests SET text = ? WHERE id = ?", (text, request_id,)
    )
    db.commit()


async def update_request_datetime(request_id, datetime: str):
    cur.execute(
        "UPDATE requests SET datetime = ? WHERE id = ?", (datetime, request_id,)
    )
    db.commit()


async def get_users():
    req = cur.execute(
        "SELECT * FROM users "
    )
    return req.fetchall()


async def get_users_sorted_by_points():
    req = cur.execute(
        "SELECT * FROM users ORDER BY points"
    )
    return req.fetchall()


async def get_admins():
    req = cur.execute(
        "SELECT surname, first_name, username FROM users WHERE role = ?", (1,)
    )
    return req.fetchall()


async def get_all_users():
    result = cur.execute(
        "SELECT * FROM users ORDER BY surname"
    )
    return result.fetchall()


async def get_user_requests(author_id: int):
    result = cur.execute(
        "SELECT * FROM requests WHERE author_id = ?", (author_id,)
    )
    return result.fetchall()


async def add_report(author_id, earned, done_tasks, not_done_tasks, scheduled_tasks):
    cur.execute(
        "INSERT INTO reports (author_id, earned, done_tasks, not_done_tasks, scheduled_tasks) "
        "values (?, ?, ?, ?, ?)", (author_id, earned, done_tasks, not_done_tasks, scheduled_tasks,)
    )
    db.commit()


async def get_user_last_request_id(user_id: int):
    result = cur.execute("SELECT id FROM requests WHERE author_id = ? ORDER BY id DESC LIMIT 1",
                         (user_id,))
    return result.fetchone()


async def get_user_last_report_id(user_id: int):
    result = cur.execute("SELECT id FROM reports WHERE author_id = ? ORDER BY id DESC LIMIT 1",
                         (user_id,))
    return result.fetchone()


async def add_message_id_to_report(report_id, message_id: int):
    cur.execute(
        "UPDATE reports SET message_id = ? WHERE id = ?", (message_id, report_id,)
    )
    db.commit()


async def get_user_reports(author_id: int):
    result = cur.execute(
        "SELECT * FROM reports WHERE author_id = ?", (author_id,)
    )
    return result.fetchall()


async def update_user_status(user_id: int, status: str):
    cur.execute(
        "UPDATE users SET status = ? WHERE id = ?", (status, user_id,)
    )
    db.commit()


async def update_report_earned(report_id: int, earned: int):
    cur.execute(
        "UPDATE reports SET earned = ? WHERE id = ?", (earned, report_id,)
    )
    db.commit()


async def get_report_by_id(report_id):
    result = cur.execute(
        "SELECT * FROM reports WHERE id = ?", (report_id,)
    )
    return result.fetchone()


async def update_report_done_tasks(report_id, done_tasks):
    cur.execute(
        "UPDATE reports SET done_tasks = ? WHERE id = ?", (done_tasks, report_id,)
    )
    db.commit()


async def update_report_not_done_tasks(report_id, not_done_tasks):
    cur.execute(
        "UPDATE reports SET not_done_tasks = ? WHERE id = ?", (not_done_tasks, report_id,)
    )
    db.commit()


async def update_report_scheduled_tasks(report_id, scheduled_tasks):
    cur.execute(
        "UPDATE reports SET scheduled_tasks = ? WHERE id = ?", (scheduled_tasks, report_id,)
    )
    db.commit()


async def count_user_reports(user_id: int):
    return cur.execute(
        "SELECT COUNT(author_id) FROM reports WHERE author_id = ?", (user_id,)
    )


async def get_user_points(user_id: int):
    result = cur.execute(
        "SELECT points FROM users WHERE id = ?", (user_id,)
    )
    return float(result.fetchone()[0])


async def update_user_points(user_id: int, points: int):
    cur.execute(
        "UPDATE users SET points = ? WHERE id = ?", (points, user_id,)
    )
    db.commit()


async def get_user_by_username(username: str):
    result = cur.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    )
    return result.fetchone()


async def get_user_status_by_id(user_id: int):
    result = cur.execute(
        "SELECT status FROM users WHERE id = ?", (user_id,)
    )
    return result.fetchone()[0]


async def close():
    """Закрываем соединение с БД"""
    db.close()
