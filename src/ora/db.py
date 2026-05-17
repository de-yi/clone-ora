"""SQLite connection + schema init."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ora import config


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def cursor():
    conn = connect()
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def init_schema(schema_path: Path | None = None) -> None:
    path = schema_path or config.SCHEMA_PATH
    sql = path.read_text(encoding="utf-8")
    conn = connect()
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
