"""Per-item task lists."""
from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("tasks", __name__)


@bp.route("/api/task/<item_id>", methods=["POST"])
def add_task(item_id):
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    conn = get_db()
    cur = conn.execute("INSERT INTO tasks (item_id, text) VALUES (?,?)", (item_id, text))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": new_id})


@bp.route("/api/task/<int:task_id>", methods=["PATCH"])
def toggle_task(task_id):
    data = request.get_json() or {}
    done = 1 if data.get("done") else 0
    conn = get_db()
    conn.execute("UPDATE tasks SET done=? WHERE id=?", (done, task_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/task/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
