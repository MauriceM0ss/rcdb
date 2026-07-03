"""Per-item notes."""
from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("notes", __name__)


@bp.route("/api/note/<item_id>", methods=["POST"])
def add_note(item_id):
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    conn = get_db()
    cur = conn.execute("INSERT INTO notes (item_id, content) VALUES (?,?)", (item_id, content))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": new_id})


@bp.route("/api/note/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    conn = get_db()
    conn.execute("UPDATE notes SET content=? WHERE id=?", (content, note_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/note/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
