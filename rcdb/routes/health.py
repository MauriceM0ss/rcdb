"""Liveness/readiness probe for container health checks."""
from flask import Blueprint, jsonify

from ..db import get_db

bp = Blueprint("health", __name__)


@bp.route("/healthz")
def healthz():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        return jsonify({"status": "error"}), 503
    return jsonify({"status": "ok"})
