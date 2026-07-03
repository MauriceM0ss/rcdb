"""Category management."""
from flask import Blueprint, jsonify, request

from ..db import get_categories, get_db

bp = Blueprint("categories", __name__)


@bp.route("/api/categories")
def list_categories():
    return jsonify(get_categories())


@bp.route("/api/categories", methods=["POST"])
def add_category():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
    except Exception:
        conn.close()
        return jsonify({"error": "already exists"}), 409
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/categories/<path:name>", methods=["PUT"])
def rename_category(name):
    data = request.get_json() or {}
    new_name = data.get("new_name", "").strip()
    if not new_name:
        return jsonify({"error": "new_name required"}), 400
    conn = get_db()
    try:
        conn.execute("UPDATE categories SET name=? WHERE name=?", (new_name, name))
        conn.execute("UPDATE items SET category=? WHERE category=?", (new_name, name))
        conn.commit()
    except Exception:
        conn.close()
        return jsonify({"error": "name already exists"}), 409
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/categories/<path:name>", methods=["DELETE"])
def delete_category(name):
    conn = get_db()
    cats = [r["name"] for r in conn.execute(
        "SELECT name FROM categories WHERE name != ? ORDER BY name", (name,)).fetchall()]
    fallback = cats[0] if cats else "Other"
    conn.execute("UPDATE items SET category=? WHERE category=?", (fallback, name))
    conn.execute("DELETE FROM categories WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "fallback": fallback})
