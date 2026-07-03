"""Item CRUD, the sidebar tree, and the hardware-template feed."""
from flask import Blueprint, jsonify, request

from ..db import get_categories, get_db
from ..hardware import HARDWARE_TEMPLATES
from ..helpers import normalize_id

bp = Blueprint("items", __name__)


@bp.route("/api/tree")
def tree_data():
    conn = get_db()
    cats = get_categories()
    rows = conn.execute("SELECT item_id, name, category FROM items ORDER BY name").fetchall()
    conn.close()
    cat_map: dict[str, list] = {c: [] for c in cats}
    for row in rows:
        c = row["category"]
        cat_map.setdefault(c, [])
        cat_map[c].append({"id": row["item_id"], "name": row["name"]})
    result = [
        {"category": c, "items": sorted(cat_map.get(c, []), key=lambda x: x["name"].lower())}
        for c in cats
    ]
    return jsonify(result)


@bp.route("/api/hardware-templates")
def get_hw_templates():
    return jsonify(HARDWARE_TEMPLATES)


@bp.route("/api/item", methods=["POST"])
def create_item():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    category      = data.get("category", "Desktops")
    hardware_type = data.get("hardware_type", "")
    item_id = normalize_id(name)
    conn = get_db()
    conn.execute(
        "INSERT INTO items (item_id, name, category, hardware_type) VALUES (?,?,?,?)",
        (item_id, name, category, hardware_type))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "item_id": item_id})


@bp.route("/api/item/<item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.get_json() or {}
    allowed = ("name", "category", "description", "hardware_type", "url", "year")
    field = data.get("field")
    if field not in allowed:
        return jsonify({"error": f"field must be one of {allowed}"}), 400
    content = data.get("content", "")
    conn = get_db()
    conn.execute(f"UPDATE items SET {field}=? WHERE item_id=?", (content, item_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/item/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    conn = get_db()
    for table in ("items", "photos", "notes", "tasks", "specs", "manual_files", "gallery_photos"):
        conn.execute(f"DELETE FROM {table} WHERE item_id=?", (item_id,))
    conn.execute("DELETE FROM item_manuals WHERE item_id=? OR manual_id=?", (item_id, item_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
