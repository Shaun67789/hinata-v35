import sqlite3
import json
import os
import time
from datetime import datetime, timedelta


DB_FILE = "bot.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        joined_at TEXT,
        last_active_at TEXT,
        message_count INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0,
        language_code TEXT
    )''')
    
    # Groups Table
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        title TEXT,
        type TEXT,
        added_at TEXT,
        last_active_at TEXT,
        member_count INTEGER DEFAULT 0
    )''')
    
    # Broadcasts Table
    c.execute('''CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        target TEXT,
        sent_count INTEGER,
        failed_count INTEGER,
        timestamp TEXT,
        message_ids TEXT -- JSON string of {chat_id: message_id}
    )''')
    
    # Chat History Table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user_id INTEGER,
        role TEXT, -- 'user' or 'hinata'
        message TEXT,
        timestamp TEXT
    )''')
    
    # Whisper Messages Table
    c.execute('''CREATE TABLE IF NOT EXISTS whisper_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        sender_name TEXT,
        sender_username TEXT,
        target_id INTEGER NOT NULL,
        target_name TEXT,
        target_username TEXT,
        group_id INTEGER NOT NULL,
        group_title TEXT,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT,
        read_at TEXT
    )''')

    conn.commit()
    conn.close()
    
    # Run migration if needed
    if is_db_empty():
        migrate_from_json()

def is_db_empty():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM users")
    user_count = c.fetchone()[0]
    conn.close()
    return user_count == 0

def migrate_from_json():
    print("Migrating data from JSON to SQLite...")
    conn = get_connection()
    c = conn.cursor()
    
    # Migrate Users
    if os.path.exists("users.json"):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    users = json.loads(content)
                    for u in users:
                        if isinstance(u, dict):
                            uid = u.get("id")
                            name = u.get("name")
                            username = u.get("username")
                            joined = u.get("joined_at", time.strftime("%Y-%m-%d %H:%M:%S"))
                            c.execute("INSERT OR IGNORE INTO users (id, full_name, username, joined_at) VALUES (?, ?, ?, ?)",
                                      (uid, name, username, joined))
                        else:
                            # Legacy list of IDs
                            c.execute("INSERT OR IGNORE INTO users (id, full_name, username, joined_at) VALUES (?, ?, ?, ?)",
                                      (u, "Legacy User", "unknown", time.strftime("%Y-%m-%d %H:%M:%S")))
        except Exception as e:
            print(f"Error migrating users: {e}")

    # Migrate Groups
    if os.path.exists("groups.json"):
        try:
            with open("groups.json", "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    groups = json.loads(content)
                    for g in groups:
                        if isinstance(g, dict):
                            gid = g.get("id")
                            title = g.get("title")
                            gtype = g.get("type", "supergroup")
                            added = g.get("added_at", time.strftime("%Y-%m-%d %H:%M:%S"))
                            c.execute("INSERT OR IGNORE INTO groups (id, title, type, added_at) VALUES (?, ?, ?, ?)",
                                      (gid, title, gtype, added))
                        else:
                            c.execute("INSERT OR IGNORE INTO groups (id, title, type, added_at) VALUES (?, ?, ?, ?)",
                                      (g, "Legacy Group", "supergroup", time.strftime("%Y-%m-%d %H:%M:%S")))
        except Exception as e:
            print(f"Error migrating groups: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

# --- User Operations ---

def add_user(user_id, full_name, username):
    conn = get_connection()
    c = conn.cursor()
    
    # Upsert logic
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if exists
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    exists = c.fetchone()
    
    if exists:
        # Update
        c.execute("UPDATE users SET full_name = ?, username = ?, last_active_at = ? WHERE id = ?",
                  (full_name, username, now, user_id))
    else:
        # Insert
        c.execute("INSERT INTO users (id, full_name, username, joined_at, last_active_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, full_name, username, now, now))
        
    conn.commit()
    conn.close()
    return not exists # Returns True if new user

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY joined_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def increment_message_count(user_id: int, full_name: str = None, username: str = None, amount: int = 1):
    """Increment message count for the user and update last active time."""
    conn = get_connection()
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Ensure user exists (upsert)
    if full_name is not None and username is not None:
        add_user(user_id, full_name, username)
    else:
        # In case user isn't registered yet, create without name
        if not get_user(user_id):
            c.execute("INSERT OR IGNORE INTO users (id, full_name, username, joined_at, last_active_at) VALUES (?, ?, ?, ?, ?)",
                      (user_id, "Unknown", "", now, now))
            conn.commit()

    c.execute("UPDATE users SET message_count = message_count + ?, last_active_at = ? WHERE id = ?", (amount, now, user_id))
    conn.commit()
    conn.close()

def get_total_messages():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(message_count) as total FROM users")
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 0

# --- Group Operations ---

def add_group(chat_id, title, chat_type):
    conn = get_connection()
    c = conn.cursor()
    
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("SELECT id FROM groups WHERE id = ?", (chat_id,))
    exists = c.fetchone()
    
    if exists:
        c.execute("UPDATE groups SET title = ?, last_active_at = ? WHERE id = ?", (title, now, chat_id))
    else:
        c.execute("INSERT INTO groups (id, title, type, added_at, last_active_at) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, title, chat_type, now, now))
                  
    conn.commit()
    conn.close()

def get_all_groups():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM groups ORDER BY added_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_group(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM groups WHERE id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def remove_group(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM groups WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()

def get_users_in_chat(chat_id):
    """Get all distinct users who have been active in a specific chat (from chat_history)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT ch.user_id,
            u.full_name,
            u.username,
            u.message_count,
            u.last_active_at,
            u.joined_at
        FROM chat_history ch
        LEFT JOIN users u ON u.id = ch.user_id
        WHERE ch.chat_id = ?
        ORDER BY u.message_count DESC
    """, (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Broadcast Operations ---

def add_broadcast(text, target, sent, failed, message_ids_map):
    conn = get_connection()
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO broadcasts (text, target, sent_count, failed_count, timestamp, message_ids) VALUES (?, ?, ?, ?, ?, ?)",
              (text, target, sent, failed, now, json.dumps(message_ids_map)))
    conn.commit()
    conn.close()

def get_all_broadcasts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM broadcasts ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_broadcast(b_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM broadcasts WHERE id = ?", (b_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_broadcast_record(b_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM broadcasts WHERE id = ?", (b_id,))
    conn.commit()
    conn.close()

# --- Chat History Operations ---

def save_chat_history(chat_id, user_id, role, message):
    conn = get_connection()
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat_history (chat_id, user_id, role, message, timestamp) VALUES (?, ?, ?, ?, ?)",
              (chat_id, user_id, role, message, now))
    conn.commit()
    conn.close()

def get_chat_history(chat_id, limit=10, max_age_seconds=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT role, message, timestamp FROM chat_history WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?", (chat_id, limit))
    rows = c.fetchall()
    conn.close()
    
    valid_history = []
    now = datetime.now()
    for row in rows:
        try:
            msg_time = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            if (now - msg_time).total_seconds() <= max_age_seconds:
                valid_history.append({"role": row["role"], "message": row["message"]})
        except ValueError:
            pass # Skip invalid dates

    # Return in chronological order
    return list(reversed(valid_history))

def clear_chat_history(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# --- Whisper Message Operations ---

def save_whisper(sender_id, sender_name, sender_username, target_id, target_name, target_username, group_id, group_title, message):
    """Save a new whisper message to the database."""
    conn = get_connection()
    c = conn.cursor()
    
    # Auto-cleanup to prevent DB bloat from inline queries
    c.execute("DELETE FROM whisper_messages WHERE is_read=0 AND created_at < datetime('now', 'localtime', '-1 day')")
    
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """INSERT INTO whisper_messages
           (sender_id, sender_name, sender_username, target_id, target_name, target_username,
            group_id, group_title, message, is_read, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (sender_id, sender_name, sender_username, target_id, target_name, target_username,
         group_id, group_title, message, now)
    )
    whisper_id = c.lastrowid
    conn.commit()
    conn.close()
    return whisper_id

def get_whisper(whisper_id):
    """Retrieve a whisper message by ID."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM whisper_messages WHERE id = ?", (whisper_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_whisper_read(whisper_id):
    """Mark a whisper as read."""
    conn = get_connection()
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE whisper_messages SET is_read = 1, read_at = ? WHERE id = ?", (now, whisper_id))
    conn.commit()
    conn.close()

def get_whisper_stats():
    """Return total whispers sent, read, and unread."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM whisper_messages")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM whisper_messages WHERE is_read = 1")
    read = c.fetchone()[0]
    conn.close()
    return {"total": total, "read": read, "unread": total - read}

def get_recent_whisper_targets(sender_id, limit=5):
    """Retrieve recent unique whisper targets for a user."""
    conn = get_connection()
    # Ensure row_factory is used
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        '''SELECT target_username, target_name, MAX(id) as max_id 
           FROM whisper_messages 
           WHERE sender_id = ? AND target_username != ''
           GROUP BY target_username, target_name
           ORDER BY max_id DESC LIMIT ?''', 
        (sender_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [{"target_username": row["target_username"], "target_name": row["target_name"]} for row in rows]
