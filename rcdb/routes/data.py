"""Whole-database operations: reset, export and import."""
import io
import os
import sqlite3

from flask import Blueprint, abort, jsonify, request, send_file

from ..config import DB_PATH, DEFAULT_CATEGORIES
from ..db import get_db

bp = Blueprint("data", __name__)


@bp.route("/api/reset", methods=["POST"])
def reset_data():
    conn = get_db()
    for table in ("item_manuals", "manual_files", "gallery_photos",
                  "specs", "tasks", "notes", "photos", "items", "categories"):
        conn.execute(f"DELETE FROM {table}")
    for cat in DEFAULT_CATEGORIES:
        conn.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/export")
def export_db():
    if not DB_PATH.exists():
        abort(404)
    tmp = DB_PATH.parent / "rcdb_export.db"
    tmp.unlink(missing_ok=True)
    conn = get_db()
    conn.execute(f"VACUUM INTO '{tmp}'")
    conn.close()
    file_bytes = tmp.read_bytes()
    tmp.unlink(missing_ok=True)
    return send_file(io.BytesIO(file_bytes), as_attachment=True,
                     download_name="rcdb.db", mimetype="application/x-sqlite3")


@bp.route("/api/import", methods=["POST"])
def import_db():
    if "db" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    data = request.files["db"].read()
    if len(data) < 16 or data[:16] != b"SQLite format 3\x00":
        return jsonify({"error": "Not a valid SQLite database"}), 400
    tmp = DB_PATH.parent / "rcdb_import.db"
    tmp.write_bytes(data)
    try:
        test = sqlite3.connect(str(tmp))
        test.execute("SELECT 1 FROM sqlite_master")
        test.close()
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return jsonify({"error": f"Invalid file: {e}"}), 400
    os.replace(str(tmp), str(DB_PATH))
    return jsonify({"ok": True})
