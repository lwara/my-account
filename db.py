import os
import sqlite3
import hashlib
import binascii
from typing import Optional


DEFAULT_DB = os.path.join(os.path.dirname(__file__), "users.db")


def get_conn(db_path: str = DEFAULT_DB):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            iterations INTEGER NOT NULL
        )
        """
    )
    # profiles table to store user details
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            address TEXT,
            email TEXT,
            phone TEXT,
            club_size TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    # fittings table to store scheduled fittings and swing analyses
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fittings (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            comments TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 100000):
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return binascii.hexlify(hashed).decode(), binascii.hexlify(salt).decode(), iterations


def create_user(username: str, password: str, db_path: str = DEFAULT_DB) -> bool:
    init_db(db_path)
    pwd_hash, salt_hex, iterations = _hash_password(password)
    conn = get_conn(db_path)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, iterations) VALUES (?, ?, ?, ?)",
            (username, pwd_hash, salt_hex, iterations),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(username: str, db_path: str = DEFAULT_DB):
    init_db(db_path)
    conn = get_conn(db_path)
    cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_id(username: str, db_path: str = DEFAULT_DB):
    user = get_user(username, db_path)
    return user["id"] if user else None


def save_profile(username: str, full_name: str = None, address: str = None, email: str = None, phone: str = None, club_size: str = None, db_path: str = DEFAULT_DB):
    init_db(db_path)
    user_id = get_user_id(username, db_path)
    if user_id is None:
        return False
    conn = get_conn(db_path)
    cur = conn.cursor()
    # Upsert profile
    cur.execute("SELECT 1 FROM profiles WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()
    if exists:
        cur.execute(
            "UPDATE profiles SET full_name=?, address=?, email=?, phone=?, club_size=? WHERE user_id=?",
            (full_name, address, email, phone, club_size, user_id),
        )
    else:
        cur.execute(
            "INSERT INTO profiles (user_id, full_name, address, email, phone, club_size) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, full_name, address, email, phone, club_size),
        )
    conn.commit()
    conn.close()
    return True


def get_profile(username: str, db_path: str = DEFAULT_DB):
    init_db(db_path)
    user_id = get_user_id(username, db_path)
    if user_id is None:
        return None
    conn = get_conn(db_path)
    cur = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_fitting(username: str, kind: str, scheduled_at: str, comments: str = None, db_path: str = DEFAULT_DB):
    """Create a new fitting/swing analysis. `scheduled_at` should be ISO datetime string."""
    init_db(db_path)
    user_id = get_user_id(username, db_path)
    if user_id is None:
        return None
    from datetime import datetime

    created_at = datetime.utcnow().isoformat()
    status = "Fitting Request Submitted"
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO fittings (user_id, kind, scheduled_at, comments, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, kind, scheduled_at, comments, status, created_at),
    )
    fitting_id = cur.lastrowid
    conn.commit()
    conn.close()
    return fitting_id


def list_fittings(username: str, db_path: str = DEFAULT_DB):
    init_db(db_path)
    user_id = get_user_id(username, db_path)
    if user_id is None:
        return []
    conn = get_conn(db_path)
    cur = conn.execute("SELECT * FROM fittings WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_fitting(fitting_id: int, db_path: str = DEFAULT_DB):
    init_db(db_path)
    conn = get_conn(db_path)
    cur = conn.execute("SELECT * FROM fittings WHERE id = ?", (fitting_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_fitting_status(fitting_id: int, status: str, db_path: str = DEFAULT_DB):
    init_db(db_path)
    conn = get_conn(db_path)
    conn.execute("UPDATE fittings SET status = ? WHERE id = ?", (status, fitting_id))
    conn.commit()
    conn.close()


def verify_password(username: str, password: str, db_path: str = DEFAULT_DB) -> bool:
    # Retrieve user from DB
    # compare with the stored hash
    user = get_user(username, db_path)
    if not user:
        return False
    salt = binascii.unhexlify(user["salt"]) # conevert hex back to bytes
    iterations = int(user["iterations"])
    hashed, _, _ = _hash_password(password, salt, iterations)
    return hashed == user["password_hash"]
