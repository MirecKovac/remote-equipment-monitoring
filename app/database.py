"""
database.py
------------
SQLite vrstva na ukladanie histórie meraní a alarmov, oddelené podľa linky
(line_id), aby dashboard zvládal viac zariadení naraz.
"""

import csv
import io
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
            line_id TEXT NOT NULL,
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
            line_id TEXT NOT NULL,
            timestamp REAL NOT NULL,
            message TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def insert_reading(line_id: str, reading) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (line_id, timestamp, temperature_c, pressure_bar, cycle_count, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            line_id,
            reading.timestamp,
            reading.temperature_c,
            reading.pressure_bar,
            reading.cycle_count,
            reading.status.value,
        ),
    )
    conn.commit()
    conn.close()


def insert_alarm(line_id: str, timestamp: float, message: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO alarms (line_id, timestamp, message, acknowledged) VALUES (?, ?, ?, 0)",
        (line_id, timestamp, message),
    )
    conn.commit()
    conn.close()


def acknowledge_alarms(line_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE alarms SET acknowledged = 1 WHERE acknowledged = 0 AND line_id = ?",
        (line_id,),
    )
    conn.commit()
    conn.close()


def get_history(line_id: str, limit: int = 100) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM readings WHERE line_id = ? ORDER BY id DESC LIMIT ?",
        (line_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def get_alarms(line_id: str, limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alarms WHERE line_id = ? ORDER BY id DESC LIMIT ?",
        (line_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def export_history_csv(line_id: str) -> str:
    """Vráti celú históriu danej linky ako CSV text."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT timestamp, temperature_c, pressure_bar, cycle_count, status "
        "FROM readings WHERE line_id = ? ORDER BY id ASC",
        (line_id,),
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "temperature_c", "pressure_bar", "cycle_count", "status"])
    for row in rows:
        writer.writerow(
            [row["timestamp"], row["temperature_c"], row["pressure_bar"], row["cycle_count"], row["status"]]
        )
    return output.getvalue()
