"""
database.py
------------
Jednoduchá SQLite vrstva na ukladanie histórie meraní a alarmov, aby
dashboard vedel zobraziť trendy a log porúch aj po reštarte servera.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            temperature_c REAL NOT NULL,
            pressure_bar REAL NOT NULL,
            cycle_count INTEGER NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            message TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def insert_reading(reading) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (timestamp, temperature_c, pressure_bar, cycle_count, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            reading.timestamp,
            reading.temperature_c,
            reading.pressure_bar,
            reading.cycle_count,
            reading.status.value,
        ),
    )
    conn.commit()
    conn.close()


def insert_alarm(timestamp: float, message: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO alarms (timestamp, message, acknowledged) VALUES (?, ?, 0)",
        (timestamp, message),
    )
    conn.commit()
    conn.close()


def acknowledge_alarms() -> None:
    conn = get_connection()
    conn.execute("UPDATE alarms SET acknowledged = 1 WHERE acknowledged = 0")
    conn.commit()
    conn.close()


def get_history(limit: int = 100) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def get_alarms(limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alarms ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
