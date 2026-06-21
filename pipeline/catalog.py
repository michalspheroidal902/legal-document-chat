"""SQLite catalog — durable app state for the local UI (matters, documents, threads).

One responsibility: persistence. All queries are parameterized (no string
interpolation). The DB lives at pipeline/.kb_catalog.db (git-ignored, D-28) and is
overridable via ``db_path`` for tests. Matter slugs are path-safe (validated here so
no caller can inject a path).
"""

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = PIPELINE_DIR / ".kb_catalog.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS matters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    display_name TEXT UNIQUE NOT NULL,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_slug TEXT NOT NULL,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    checksum TEXT,
    size_bytes INTEGER,
    status TEXT NOT NULL,
    reason TEXT,
    updated TEXT NOT NULL,
    FOREIGN KEY (matter_slug) REFERENCES matters(slug)
);
CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_slug TEXT NOT NULL,
    title TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    citations_json TEXT,
    created TEXT NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(db_path=None):
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def slugify(name):
    """Path-safe slug: lowercase, non-alphanumeric -> '-', collapsed, trimmed."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")


# --- matters -----------------------------------------------------------------

def create_matter(display_name, db_path=None):
    name = (display_name or "").strip()
    if not name:
        raise ValueError("display_name is required")
    slug = slugify(name)
    if not slug:
        raise ValueError("display_name has no usable (alphanumeric) characters")
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO matters (slug, display_name, created) VALUES (?, ?, ?)",
            (slug, name, _now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM matters WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        raise ValueError(f"matter already exists: {name!r}")
    finally:
        conn.close()


def list_matters(db_path=None):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT m.*, (SELECT COUNT(*) FROM documents d WHERE d.matter_slug = m.slug) "
            "AS doc_count FROM matters m ORDER BY m.display_name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_matter(slug, db_path=None):
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT * FROM matters WHERE slug = ?", (slug,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
