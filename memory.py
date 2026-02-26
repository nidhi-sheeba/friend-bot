# memory.py
import sqlite3
import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

DB_PATH = "chat_memory.db"


def init_db():
    """
    Creates the database and messages table if they don't exist yet.
    Called once when the bot starts.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()   # save changes
    conn.close()    # always close connections when done


def save_message(user_id: str, role: str, content: str):
    """
    Saves a single message to the database.
    role is either 'human' or 'ai'
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )

    conn.commit()
    conn.close()


def load_history(user_id: str, limit: int = 20) -> list:
    """
    Loads the last N messages for a user.
    Returns them as LangChain message objects ready to send to the LLM.
    limit=20 means last 20 messages (10 exchanges) — enough context, not too expensive
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, content FROM messages
        WHERE user_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
    """, (user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    messages = []
    for role, content in rows:
        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))

    return messages


def clear_history(user_id: str):
    """
    Deletes all messages for a user.
    Called when they use /tone to reset — fresh start.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()