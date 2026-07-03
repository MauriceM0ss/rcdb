"""HTML page views: the item grid and the item detail page."""
from flask import Blueprint, abort, render_template, request

from ..db import get_categories, get_db
from ..hardware import (
    DESKTOP_SPEC_HW_MAP,
    DESKTOP_SPECS,
    HARDWARE_TEMPLATES,
    LAPTOP_SPECS,
)

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    cat_filter = request.args.get("cat", "")
    conn = get_db()
    if cat_filter:
        rows = conn.execute(
            "SELECT item_id, name, category FROM items WHERE category=? ORDER BY name",
            (cat_filter,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT item_id, name, category FROM items ORDER BY category, name").fetchall()
    photo_ids = {r["item_id"] for r in conn.execute("SELECT item_id FROM photos").fetchall()}
    conn.close()
    items = [
        {"id": r["item_id"], "name": r["name"], "category": r["category"],
         "has_photo": r["item_id"] in photo_ids}
        for r in rows
    ]
    return render_template("index.html", items=items, categories=get_categories(),
                           active_cat=cat_filter)


@bp.route("/item/<item_id>")
def item_detail(item_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM items WHERE item_id=?", (item_id,)).fetchone()
    if not row:
        abort(404)
    has_photo = conn.execute("SELECT 1 FROM photos WHERE item_id=?", (item_id,)).fetchone()
    db_notes = conn.execute(
        "SELECT id, content, created_at FROM notes WHERE item_id=? ORDER BY id DESC",
        (item_id,)).fetchall()
    db_tasks = conn.execute(
        "SELECT id, text, done FROM tasks WHERE item_id=? ORDER BY done ASC, id ASC",
        (item_id,)).fetchall()
    db_specs = conn.execute(
        "SELECT id, key, value FROM specs WHERE item_id=? ORDER BY sort_order ASC, id ASC",
        (item_id,)).fetchall()
    item = {
        "id": row["item_id"], "name": row["name"], "category": row["category"],
        "description": row["description"], "created_at": row["created_at"],
        "hardware_type": row["hardware_type"], "url": row["url"], "year": row["year"],
        "has_photo": has_photo is not None,
    }
    notes = [{"id": r["id"], "content": r["content"], "created_at": r["created_at"]}
             for r in db_notes]
    tasks = [{"id": r["id"], "text": r["text"], "done": bool(r["done"])} for r in db_tasks]
    specs_by_key = {r["key"]: {"id": r["id"], "value": r["value"]} for r in db_specs}

    hw_items_by_type: dict[str, list] = {}
    if row["category"] == "Desktops":
        hw_rows = conn.execute(
            "SELECT item_id, name, hardware_type FROM items "
            "WHERE category='Hardware' AND hardware_type != '' ORDER BY name"
        ).fetchall()
        for hw in hw_rows:
            hw_items_by_type.setdefault(hw["hardware_type"], []).append(
                {"id": hw["item_id"], "name": hw["name"]}
            )

    gallery_photo_ids: list = []
    if row["category"] in ("Desktops", "Laptops", "Hardware"):
        gp_rows = conn.execute(
            "SELECT id FROM gallery_photos WHERE item_id=? ORDER BY uploaded_at",
            (item_id,)
        ).fetchall()
        gallery_photo_ids = [r["id"] for r in gp_rows]

    manual_files: list = []
    if row["category"] == "Manuals":
        mf_rows = conn.execute(
            "SELECT id, filename, mimetype, size FROM manual_files "
            "WHERE item_id=? ORDER BY uploaded_at DESC", (item_id,)
        ).fetchall()
        manual_files = [{"id": r["id"], "filename": r["filename"],
                         "mimetype": r["mimetype"], "size": r["size"]} for r in mf_rows]

    linked_manuals: list = []
    all_manuals: list = []
    if row["category"] in ("Desktops", "Laptops", "Hardware"):
        lm_rows = conn.execute(
            "SELECT im.id, im.manual_id, i.name FROM item_manuals im "
            "JOIN items i ON i.item_id = im.manual_id "
            "WHERE im.item_id=? ORDER BY i.name", (item_id,)
        ).fetchall()
        linked_manuals = [{"id": r["id"], "manual_id": r["manual_id"], "name": r["name"]}
                          for r in lm_rows]
        am_rows = conn.execute(
            "SELECT item_id, name FROM items WHERE category='Manuals' ORDER BY name"
        ).fetchall()
        all_manuals = [{"id": r["item_id"], "name": r["name"]} for r in am_rows]

    conn.close()

    return render_template("item.html", item=item, notes=notes, tasks=tasks,
                           specs_by_key=specs_by_key, categories=get_categories(),
                           hardware_templates=HARDWARE_TEMPLATES,
                           desktop_specs=DESKTOP_SPECS, laptop_specs=LAPTOP_SPECS,
                           hw_items_by_type=hw_items_by_type,
                           desktop_spec_hw_map=DESKTOP_SPEC_HW_MAP,
                           gallery_photo_ids=gallery_photo_ids,
                           manual_files=manual_files,
                           linked_manuals=linked_manuals,
                           all_manuals=all_manuals)
