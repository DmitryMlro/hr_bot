import sqlite3
from datetime import datetime
import uuid
from typing import List, Tuple, Optional

DB_NAME = "hr_bot.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id   INTEGER PRIMARY KEY,
                full_name     TEXT    NOT NULL,
                department    TEXT    NOT NULL,
                position      TEXT    NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER,
                request_number   INTEGER,
                category         TEXT,
                text             TEXT,
                status           TEXT    DEFAULT 'Відправлено',
                response         TEXT,
                assigned_hr_id   INTEGER,
                created_at       TEXT,
                updated_at       TEXT,
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS anonymous_feedback (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER,
                text             TEXT    NOT NULL,
                response         TEXT,
                assigned_hr_id   INTEGER,
                created_at       TEXT    NOT NULL,
                responded_at     TEXT,
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS hr_tokens (
                token   TEXT PRIMARY KEY,
                is_used INTEGER NOT NULL DEFAULT 0
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                telegram_id INTEGER PRIMARY KEY,
                role        TEXT    NOT NULL
            )
        ''')

        conn.commit()


def get_user_role(telegram_id: int) -> Optional[str]:
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT role FROM roles WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchone()
    return row[0] if row else None


def has_hr_access(telegram_id: int) -> bool:
    return get_user_role(telegram_id) == "hr"


def add_hr(telegram_id: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO roles (telegram_id, role) VALUES (?, 'hr')",
            (telegram_id,)
        )
        conn.commit()


def get_all_hr_ids() -> List[int]:
    with sqlite3.connect(DB_NAME) as conn:
        return [r[0] for r in conn.execute(
            "SELECT telegram_id FROM roles WHERE role = 'hr'"
        ).fetchall()]


def is_token_valid(token: str) -> bool:
    row = sqlite3.connect(DB_NAME).execute(
        "SELECT is_used FROM hr_tokens WHERE token = ?",
        (token,)
    ).fetchone()
    return bool(row and row[0] == 0)


def mark_token_as_used(token: str) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "UPDATE hr_tokens SET is_used = 1 WHERE token = ?",
            (token,)
        )
        conn.commit()


def generate_hr_token() -> str:
    token = uuid.uuid4().hex[:8]
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO hr_tokens (token) VALUES (?)", (token,))
        conn.commit()
    return token


def add_user(telegram_id: int, full_name: str, department: str, position: str) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO users
              (telegram_id, full_name, department, position)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, full_name, department, position))
        conn.commit()


def get_user(telegram_id: int) -> Optional[Tuple]:
    return sqlite3.connect(DB_NAME).execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()


def get_all_users() -> List[Tuple[int, str, str, str]]:
    return sqlite3.connect(DB_NAME).execute(
        "SELECT telegram_id, full_name, department, position FROM users"
    ).fetchall()


def update_user_info(telegram_id: int, full_name: str, department: str, position: str) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            UPDATE users
            SET full_name = ?, department = ?, position = ?
            WHERE telegram_id = ?
        ''', (full_name, department, position, telegram_id))
        conn.commit()


def delete_user(telegram_id: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        conn.execute("DELETE FROM roles WHERE telegram_id = ?", (telegram_id,))
        conn.commit()


def get_next_request_number(user_id: int) -> int:
    last = sqlite3.connect(DB_NAME).execute(
        "SELECT MAX(request_number) FROM requests WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]
    return (last or 0) + 1


def add_request(user_id: int, category: str, text: str) -> int:
    number = get_next_request_number(user_id)
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute('''
            INSERT INTO requests
              (user_id, request_number, category, text, status, created_at)
            VALUES (?, ?, ?, ?, 'Відправлено', ?)
        ''', (user_id, number, category, text, now))
        conn.commit()
        return cursor.lastrowid


def get_new_requests() -> List[Tuple[int, int, str, str, str, str, str, str]]:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute('''
            SELECT
              r.id,
              r.request_number,
              u.full_name,
              u.department,
              u.position,
              r.category,
              r.text,
              r.created_at
            FROM requests r
            JOIN users u ON r.user_id = u.telegram_id
            WHERE r.status = 'Відправлено'
            ORDER BY r.created_at ASC
        ''').fetchall()


def get_user_requests(user_id: int) -> List[Tuple]:
    return sqlite3.connect(DB_NAME).execute('''
        SELECT
          r.request_number,
          r.category,
          r.text,
          r.status,
          r.response,
          u2.full_name AS hr_name,
          r.created_at,
          r.updated_at
        FROM requests r
        LEFT JOIN users u2 ON r.assigned_hr_id = u2.telegram_id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
    ''', (user_id,)).fetchall()


def update_request_status(request_id: int, status: Optional[str] = None, response: Optional[str] = None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_NAME) as conn:
        if status is not None and response is None:
            conn.execute('''
                UPDATE requests
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', (status, now, request_id))
        elif response is not None and status is None:
            conn.execute('''
                UPDATE requests
                SET response = ?, updated_at = ?
                WHERE id = ?
            ''', (response, now, request_id))
        elif status is not None and response is not None:
            conn.execute('''
                UPDATE requests
                SET status = ?, response = ?, updated_at = ?
                WHERE id = ?
            ''', (status, response, now, request_id))
        conn.commit()


def assign_hr_to_request(request_id: int, hr_id: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "UPDATE requests SET assigned_hr_id = ? WHERE id = ?",
            (hr_id, request_id)
        )
        conn.commit()


def get_request(request_id: int) -> Tuple[int, int]:
    return sqlite3.connect(DB_NAME).execute(
        "SELECT user_id, request_number FROM requests WHERE id = ?",
        (request_id,)
    ).fetchone()


def get_feedback_user(feedback_id: int) -> Optional[int]:
    row = sqlite3.connect(DB_NAME).execute(
        "SELECT user_id FROM anonymous_feedback WHERE id = ?",
        (feedback_id,)
    ).fetchone()
    return row[0] if row else None


def add_anonymous_feedback(user_id: int, text: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT INTO anonymous_feedback
              (user_id, text, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, text, now))
        conn.commit()


def get_new_feedback() -> List[Tuple[int, str, str]]:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute('''
            SELECT id, text, created_at
            FROM anonymous_feedback
            WHERE response IS NULL
            ORDER BY created_at ASC
        ''').fetchall()


def get_user_feedback(user_id: int) -> List[Tuple]:
    return sqlite3.connect(DB_NAME).execute('''
        SELECT
          af.id,
          af.text,
          af.response,
          af.created_at,
          af.responded_at,
          hr.full_name AS hr_name
        FROM anonymous_feedback af
        LEFT JOIN users hr ON af.assigned_hr_id = hr.telegram_id
        WHERE af.user_id = ?
        ORDER BY af.created_at DESC
    ''', (user_id,)).fetchall()


def add_feedback_response(feedback_id: int, response: str, hr_id: int) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            UPDATE anonymous_feedback
            SET response = ?, responded_at = ?, assigned_hr_id = ?
            WHERE id = ?
        ''', (response, now, hr_id, feedback_id))
        conn.commit()


def get_processed_requests(limit: Optional[int] = 10) -> List[Tuple]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    base_sql = '''
        SELECT
          r.id,
          r.request_number,
          u.full_name,
          u.department,
          u.position,
          r.category,
          r.text,
          r.status,
          r.response,
          r.created_at,
          r.updated_at,
          hr.full_name
        FROM requests r
        JOIN users u ON r.user_id = u.telegram_id
        LEFT JOIN users hr ON r.assigned_hr_id = hr.telegram_id
        WHERE r.status != 'Відправлено'
        ORDER BY r.updated_at DESC
    '''
    if limit is not None:
        base_sql += ' LIMIT ?'
        cur.execute(base_sql, (limit,))
    else:
        cur.execute(base_sql)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_processed_feedbacks(limit: Optional[int] = 10) -> List[Tuple]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    base_sql = '''
        SELECT
          af.id,
          u.full_name AS user_name,
          af.text,
          af.response,
          af.created_at,
          af.responded_at,
          hr.full_name AS hr_name
        FROM anonymous_feedback af
        JOIN users u ON af.user_id = u.telegram_id
        LEFT JOIN users hr ON af.assigned_hr_id = hr.telegram_id
        WHERE af.response IS NOT NULL
        ORDER BY af.responded_at DESC
    '''
    if limit is not None:
        base_sql += ' LIMIT ?'
        cur.execute(base_sql, (limit,))
    else:
        cur.execute(base_sql)
    rows = cur.fetchall()
    conn.close()
    return rows

