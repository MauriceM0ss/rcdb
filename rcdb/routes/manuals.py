"""Manual file attachments and item↔manual links."""
import os

from flask import Blueprint, abort, jsonify, request

from ..config import ALLOWED_MANUAL_EXTS
from ..db import get_db
from ..security import safe_manual_download_response, safe_manual_view_response

bp = Blueprint("manuals", __name__)


# ── Manual files ───────────────────────────────────────────────────────────
@bp.route("/api/manual-file/<item_id>", methods=["POST"])
def upload_manual_file(item_id):
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    filename = (f.filename or "").strip()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_MANUAL_EXTS:
        return jsonify({"error": f"File type '{ext}' not allowed. Use: {', '.join(sorted(ALLOWED_MANUAL_EXTS))}"}), 400
    data = f.read()
    mime = f.mimetype or "application/octet-stream"
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO manual_files (item_id, filename, mimetype, file_data, size) VALUES (?,?,?,?,?)",
        (item_id, filename, mime, data, len(data)))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": new_id, "filename": filename,
                    "size": len(data), "mimetype": mime})


@bp.route("/api/manual-file/<int:file_id>")
def download_manual_file(file_id):
    conn = get_db()
    row = conn.execute(
        "SELECT filename, mimetype, file_data FROM manual_files WHERE id=?", (file_id,)
    ).fetchone()
    conn.close()
    if not row:
        abort(404)
    return safe_manual_download_response(row["filename"], row["file_data"])


@bp.route("/api/manual-files/<item_id>")
def list_manual_files(item_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, filename, size FROM manual_files WHERE item_id=? ORDER BY uploaded_at",
        (item_id,)
    ).fetchall()
    conn.close()
    return jsonify([{"id": r["id"], "filename": r["filename"], "size": r["size"]}
                    for r in rows])


@bp.route("/api/manual-file-view/<int:file_id>")
def view_manual_file(file_id):
    """Serve file inline (no download prompt) so the browser or JS can display it."""
    conn = get_db()
    row = conn.execute(
        "SELECT filename, mimetype, file_data FROM manual_files WHERE id=?", (file_id,)
    ).fetchone()
    conn.close()
    if not row:
        abort(404)
    return safe_manual_view_response(row["filename"], row["file_data"])


@bp.route("/api/manual-file/<int:file_id>", methods=["DELETE"])
def delete_manual_file(file_id):
    conn = get_db()
    conn.execute("DELETE FROM manual_files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ── Item ↔ manual links ────────────────────────────────────────────────────
@bp.route("/api/item-manuals/<item_id>", methods=["POST"])
def link_manual(item_id):
    data = request.get_json() or {}
    manual_id = data.get("manual_id", "").strip()
    if not manual_id:
        return jsonify({"error": "manual_id required"}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO item_manuals (item_id, manual_id) VALUES (?,?)", (item_id, manual_id))
        conn.commit()
        new_id = cur.lastrowid
    except Exception:
        conn.close()
        return jsonify({"error": "already linked"}), 409
    conn.close()
    return jsonify({"ok": True, "id": new_id})


@bp.route("/api/item-manuals/<int:link_id>", methods=["DELETE"])
def unlink_manual(link_id):
    conn = get_db()
    conn.execute("DELETE FROM item_manuals WHERE id=?", (link_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
