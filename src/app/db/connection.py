import sqlite3
import pandas as pd
from contextlib import contextmanager


from config import get_db_path
from app.ui.language import get_selected_language


@contextmanager
def get_connection():
    lang = get_selected_language()
    db_path = get_db_path(lang)

    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def run_query(query: str, params: tuple = ()):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def execute_query(query: str, params: tuple = ()):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
