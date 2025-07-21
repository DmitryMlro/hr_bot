import random
import string
import sqlite3
from database import DB_NAME

def generate_token(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

def save_token(token):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO hr_tokens (token, is_used) VALUES (?, 0)', (token,))
        conn.commit()

def generate_and_store_token():
    token = generate_token()
    save_token(token)
    return token
