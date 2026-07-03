"""Runtime configuration and small filesystem helpers.

Values are read from the environment at import time. Tests set ``DB_PATH``
before importing the app so each run gets an isolated database.
"""
import os
import secrets
from pathlib import Path

# Location of the SQLite database. The container mounts /data as a volume.
DB_PATH = Path(os.environ.get("DB_PATH", "/data/rcdb.db"))

# Categories seeded on first run and restored by a reset.
DEFAULT_CATEGORIES = ("Desktops", "Laptops", "Hardware", "Manuals")

# File extensions accepted for manual attachments.
ALLOWED_MANUAL_EXTS = {".md", ".doc", ".docx", ".pdf", ".txt"}

# Reject request bodies larger than this (uploads included) to bound disk use.
MAX_CONTENT_LENGTH = int(os.environ.get("RCDB_MAX_UPLOAD_MB", "64")) * 1024 * 1024

# Optional shared-password gate. Empty/unset ⇒ the app runs open (LAN use).
AUTH_PASSWORD = os.environ.get("RCDB_PASSWORD", "").strip()


def get_or_create_secret() -> bytes:
    """Load the Flask session secret, generating and persisting one if absent."""
    p = DB_PATH.parent / "app_secret.key"
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        return p.read_bytes()
    k = secrets.token_bytes(32)
    p.write_bytes(k)
    return k
