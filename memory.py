# memory.py
import os
import sqlite3
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# ── DETECT WHICH DATABASE TO USE ──────────────────────────────────────
# Locally: SQLite (simple file)
# On Railway: PostgreSQL (persistent cloud database)
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor


# ── CONNECTION HELPER ──────────────────────────────────────────────────
def get_connection():
    """Returns the right database connection based on environment"""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect("chat_memory.db")


def get_cursor(conn):
    """Returns the right cursor type"""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()


# ── INIT ───────────────────────────────────────────────────────────────
def init_db():
    conn = get_connection()
    cursor = get_cursor(conn)

    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id        SERIAL PRIMARY KEY,
                user_id   TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id        SERIAL PRIMARY KEY,
                content   TEXT NOT NULL,
                created   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                content   TEXT NOT NULL,
                created   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()


# ── SAVE MESSAGE ───────────────────────────────────────────────────────
def save_message(user_id: str, role: str, content: str):
    conn = get_connection()
    cursor = get_cursor(conn)

    if USE_POSTGRES:
        cursor.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)",
            (user_id, role, content)
        )
    else:
        cursor.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )

    conn.commit()
    conn.close()


# ── LOAD HISTORY ───────────────────────────────────────────────────────
def load_history(user_id: str, limit: int = 20) -> list:
    conn = get_connection()
    cursor = get_cursor(conn)

    if USE_POSTGRES:
        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
        """, (user_id, limit))
    else:
        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    messages = []
    for row in rows:
        # psycopg2 returns dicts, sqlite3 returns tuples — handle both
        role = row["role"] if USE_POSTGRES else row[0]
        content = row["content"] if USE_POSTGRES else row[1]

        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))

    return messages


# ── CLEAR HISTORY ──────────────────────────────────────────────────────
def clear_history(user_id: str):
    conn = get_connection()
    cursor = get_cursor(conn)

    if USE_POSTGRES:
        cursor.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
    else:
        cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()
    