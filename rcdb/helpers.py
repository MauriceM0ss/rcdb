"""Pure helpers and Jinja template registration."""
import re
import uuid
from datetime import datetime

from .db import get_db
from .hardware import HARDWARE_TEMPLATES

_PALETTE = [
    "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6",
    "#ef4444", "#06b6d4", "#f97316", "#84cc16",
]


def normalize_id(name: str) -> str:
    """Slugify a name into a URL-safe id with a short random suffix."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    base = re.sub(r"\s+", "_", s.strip()) or "item"
    return base + "_" + uuid.uuid4().hex[:6]


def cat_color(name: str) -> str:
    return _PALETTE[hash(name) % len(_PALETTE)]


def filesize_filter(n: int) -> str:
    if n < 1024:       return f"{n} B"
    if n < 1024 ** 2:  return f"{n/1024:.1f} KB"
    return f"{n/1024**2:.1f} MB"


def file_icon_filter(f: dict) -> str:
    ext = f["filename"].rsplit(".", 1)[-1].lower() if "." in f["filename"] else ""
    return {"pdf": "📄", "doc": "📝", "docx": "📝", "md": "📑", "txt": "📃"}.get(ext, "📎")


def register_template_helpers(app) -> None:
    """Wire the Jinja filters and context processor onto the app."""
    app.add_template_filter(cat_color, "cat_color")
    app.add_template_filter(filesize_filter, "filesize")
    app.add_template_filter(file_icon_filter, "file_icon")

    @app.context_processor
    def _inject():
        # Context processors only run when a template is rendered, so the JSON
        # API routes never pay for these two counts. They feed the status bar.
        conn = get_db()
        total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        total_categories = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        conn.close()
        return {
            "hw_type_names": list(HARDWARE_TEMPLATES.keys()),
            "current_year": datetime.now().year,
            "total_items": total_items,
            "total_categories": total_categories,
        }
