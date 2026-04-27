from contextlib import contextmanager
from typing import Iterable, Mapping, Any
import psycopg
from psycopg.rows import dict_row
from .settings import get_settings

@contextmanager
def get_conn():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError('DATABASE_URL is not configured')
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def fetch_all(query: str, params: tuple | dict | None = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

def fetch_one(query: str, params: tuple | dict | None = None) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

def execute_many(query: str, rows: Iterable[Mapping[str, Any]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, rows)
    return len(rows)

