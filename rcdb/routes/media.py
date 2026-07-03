"""Cover photos and gallery photos (stored as BLOBs)."""
from flask import Blueprint, abort, jsonify, request

from ..db import get_db
from ..security import safe_image_response

bp = Blueprint("media", __name__)


# ── Cover photo ────────────────────────────────────────────────────────────
@bp.route("/api/photo/<item_id>")
def get_photo(item_id):
    conn = get_db()
    row = conn.execute("SELECT photo_data, mimetype FROM photos WHERE item_id=?",
                       (item_id,)).fetchone()
    conn.close()
    if not row:
        abort(404)
    return safe_image_response(row["photo_data"], row["mimetype"])


@bp.route("/api/photo/<item_id>", methods=["POST"])
def upload_photo(item_id):
    if "photo" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["photo"]
    data = f.read()
    mime = f.mimetype or "image/jpeg"
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO photos (item_id, photo_data, mimetype) VALUES (?,?,?)",
                 (item_id, data, mime))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/photo/<item_id>", methods=["DELETE"])
def delete_photo(item_id):
    conn = get_db()
    conn.execute("DELETE FROM photos WHERE item_id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ── Gallery photos ─────────────────────────────────────────────────────────
@bp.route("/api/gallery/<item_id>", methods=["POST"])
def upload_gallery_photo(item_id):
    if "photo" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["photo"]
    data = f.read()
    mime = f.mimetype or "image/jpeg"
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO gallery_photos (item_id, photo_data, mimetype) VALUES (?,?,?)",
        (item_id, data, mime))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": new_id})


@bp.route("/api/gallery-photo/<int:photo_id>")
def get_gallery_photo(photo_id):
    conn = get_db()
    row = conn.execute(
        "SELECT photo_data, mimetype FROM gallery_photos WHERE id=?", (photo_id,)
    ).fetchone()
    conn.close()
    if not row:
        abort(404)
    return safe_image_response(row["photo_data"], row["mimetype"])


@bp.route("/api/gallery-photo/<int:photo_id>", methods=["DELETE"])
def delete_gallery_photo(photo_id):
    conn = get_db()
    conn.execute("DELETE FROM gallery_photos WHERE id=?", (photo_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
