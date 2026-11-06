import sqlite3
import os
from pathlib import Path

# Always resolve the DB path relative to this file so it works regardless of
# the current working directory when the app is started.
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "database.db")


def get_db():
    """Return an open sqlite3 connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the potholes table if it doesn't exist."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS potholes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude     REAL,
            longitude    REAL,
            status       TEXT,
            notes        TEXT,
            image        TEXT,
            confidence   REAL,
            detected_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def add_pothole(latitude, longitude, status="DISCOVERED"):
    """Manually adds a new pothole to the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO potholes (latitude, longitude, status) VALUES (?, ?, ?)",
        (latitude, longitude, status)
    )
    conn.commit()
    conn.close()


def delete_pothole(pothole_id):
    """Deletes a specific pothole from the database by its ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM potholes WHERE id = ?", (pothole_id,))
    conn.commit()
    conn.close()
