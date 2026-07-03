"""Database access and schema management."""
import sqlite3

from .config import DB_PATH, DEFAULT_CATEGORIES


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS items (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id       TEXT UNIQUE NOT NULL,
        name          TEXT NOT NULL,
        category      TEXT NOT NULL DEFAULT 'Desktops',
        description   TEXT NOT NULL DEFAULT '',
        hardware_type TEXT NOT NULL DEFAULT '',
        url           TEXT NOT NULL DEFAULT '',
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    for col in ("hardware_type TEXT NOT NULL DEFAULT ''",
                "url TEXT NOT NULL DEFAULT ''",
                "year TEXT NOT NULL DEFAULT ''"):
        try:
            conn.execute(f"ALTER TABLE items ADD COLUMN {col}")
        except Exception:
            pass
    conn.execute("""CREATE TABLE IF NOT EXISTS categories (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS photos (
        item_id    TEXT PRIMARY KEY,
        photo_data BLOB,
        mimetype   TEXT DEFAULT 'image/jpeg',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id    TEXT NOT NULL,
        content    TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id    TEXT NOT NULL,
        text       TEXT NOT NULL,
        done       INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS specs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id    TEXT NOT NULL,
        key        TEXT NOT NULL,
        value      TEXT NOT NULL DEFAULT '',
        sort_order INTEGER NOT NULL DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS gallery_photos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id     TEXT NOT NULL,
        photo_data  BLOB NOT NULL,
        mimetype    TEXT NOT NULL DEFAULT 'image/jpeg',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS manual_files (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id     TEXT NOT NULL,
        filename    TEXT NOT NULL,
        mimetype    TEXT NOT NULL DEFAULT 'application/octet-stream',
        file_data   BLOB NOT NULL,
        size        INTEGER NOT NULL DEFAULT 0,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS item_manuals (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id   TEXT NOT NULL,
        manual_id TEXT NOT NULL,
        UNIQUE(item_id, manual_id)
    )""")
    if not conn.execute("SELECT 1 FROM categories").fetchone():
        for cat in DEFAULT_CATEGORIES:
            conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
    else:
        # Migrate the legacy "Software" category to "Manuals".
        conn.execute("UPDATE categories SET name='Manuals' WHERE name='Software'")
        conn.execute("UPDATE items SET category='Manuals' WHERE category='Software'")
    conn.commit()
    conn.close()


def get_categories() -> list[str]:
    conn = get_db()
    rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]
