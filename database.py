import sqlite3
import time
import config


def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            access_key TEXT,
            leads INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0,
            balance REAL DEFAULT 0,
            paid_out REAL DEFAULT 0,
            is_active INTEGER DEFAULT 0,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            address TEXT,
            network TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL,
            processed_at REAL
        );
        CREATE TABLE IF NOT EXISTS access_keys (
            key TEXT PRIMARY KEY,
            created_at REAL,
            used_by INTEGER,
            used_at REAL
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()


def add_user(user_id, username, first_name, access_key):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, access_key, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, first_name, access_key, time.time()),
    )
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_key(key):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE access_key = ?", (key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def activate_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_active = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_leads(user_id, leads, price=None):
    if price is None:
        price = config.LEAD_PRICE
    conn = get_conn()
    earned = leads * price
    conn.execute(
        "UPDATE users SET leads = ?, total_earned = ?, balance = ? WHERE user_id = ?",
        (leads, earned, earned, user_id),
    )
    conn.commit()
    conn.close()


def add_leads(user_id, additional, price=None):
    if price is None:
        price = config.LEAD_PRICE
    conn = get_conn()
    conn.execute(
        """UPDATE users SET leads = leads + ?,
           total_earned = total_earned + ?,
           balance = balance + ? WHERE user_id = ?""",
        (additional, additional * price, additional * price, user_id),
    )
    conn.commit()
    conn.close()


def set_balance(user_id, balance):
    conn = get_conn()
    conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id))
    conn.commit()
    conn.close()


def set_paid_out(user_id, paid_out):
    conn = get_conn()
    conn.execute("UPDATE users SET paid_out = ? WHERE user_id = ?", (paid_out, user_id))
    conn.commit()
    conn.close()


def remove_user(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_active_users():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE is_active = 1").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_users(query):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users WHERE username LIKE ? OR first_name LIKE ? OR user_id LIKE ?",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_withdrawal(user_id, amount, address, network):
    conn = get_conn()
    c = conn.execute(
        "INSERT INTO withdrawals (user_id, amount, address, network, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, address, network, time.time()),
    )
    conn.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id)
    )
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def get_pending_withdrawals():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_withdrawal(withdrawal_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    row = dict(row)
    conn.execute(
        "UPDATE withdrawals SET status = 'approved', processed_at = ? WHERE id = ?",
        (time.time(), withdrawal_id),
    )
    conn.execute(
        "UPDATE users SET paid_out = paid_out + ? WHERE user_id = ?",
        (row["amount"], row["user_id"]),
    )
    conn.commit()
    conn.close()
    return row


def reject_withdrawal(withdrawal_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    row = dict(row)
    conn.execute(
        "UPDATE withdrawals SET status = 'rejected', processed_at = ? WHERE id = ?",
        (time.time(), withdrawal_id),
    )
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (row["amount"], row["user_id"]),
    )
    conn.commit()
    conn.close()
    return row


def has_pending_withdrawal(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM withdrawals WHERE user_id = ? AND status = 'pending'",
        (user_id,),
    ).fetchone()
    conn.close()
    return row is not None


def get_user_stats(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT leads, total_earned, balance, paid_out FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_total_stats():
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as total_users, SUM(leads) as total_leads, SUM(total_earned) as total_earned, SUM(paid_out) as total_paid_out FROM users"
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def add_key(key):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO access_keys (key, created_at) VALUES (?, ?)",
        (key, time.time()),
    )
    conn.commit()
    conn.close()


def use_key(key, user_id):
    conn = get_conn()
    conn.execute(
        "UPDATE access_keys SET used_by = ?, used_at = ? WHERE key = ? AND used_by IS NULL",
        (user_id, time.time(), key),
    )
    conn.commit()
    conn.close()


def is_key_valid(key):
    conn = get_conn()
    row = conn.execute(
        "SELECT used_by FROM access_keys WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row is not None and row["used_by"] is None


def get_all_keys():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM access_keys ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_key(key):
    conn = get_conn()
    conn.execute("DELETE FROM access_keys WHERE key = ? AND used_by IS NULL", (key,))
    conn.commit()
    conn.close()
