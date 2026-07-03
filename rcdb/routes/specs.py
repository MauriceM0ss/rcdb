"""Per-item structured specifications."""
from flask import Blueprint, jsonify, request

from ..db import get_db

bp = Blueprint("specs", __name__)


@bp.route("/api/spec/<item_id>", methods=["POST"])
def add_spec(item_id):
    data = request.get_json() or {}
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    if not key:
        return jsonify({"error": "key required"}), 400
    conn = get_db()
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM specs WHERE item_id=?",
        (item_id,)).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO specs (item_id, key, value, sort_order) VALUES (?,?,?,?)",
        (item_id, key, value, max_order + 1))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": new_id})


@bp.route("/api/spec/<int:spec_id>", methods=["PUT"])
def update_spec(spec_id):
    data = request.get_json() or {}
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    if not key:
        return jsonify({"error": "key required"}), 400
    conn = get_db()
    conn.execute("UPDATE specs SET key=?, value=? WHERE id=?", (key, value, spec_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/spec/<int:spec_id>", methods=["DELETE"])
def delete_spec(spec_id):
    conn = get_db()
    conn.execute("DELETE FROM specs WHERE id=?", (spec_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
