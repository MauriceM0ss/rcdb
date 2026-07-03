"""RCDB application factory.

The package is split into focused modules:
  config   — env-driven settings and the session secret
  db       — connection, schema, category helpers
  hardware — static hardware-type templates and spec layouts
  helpers  — id slug + Jinja filters/context
  routes/  — one blueprint per resource (pages, items, categories, notes,
             tasks, specs, media, manuals, data)
"""
import logging
from datetime import timedelta

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .config import MAX_CONTENT_LENGTH, get_or_create_secret
from .db import init_db
from .helpers import register_template_helpers
from .routes import register_blueprints
from .security import add_security_headers, check_auth, check_csrf

__all__ = ["create_app", "init_db"]


def _configure_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    @app.after_request
    def _log_client_errors(resp):
        if resp.status_code >= 400:
            app.logger.warning("%s %s -> %s (%s)", request.method, request.path,
                               resp.status_code, request.remote_addr)
        return resp

    @app.errorhandler(Exception)
    def _log_unhandled(e):
        # Let Flask render normal HTTP errors (404/403/401/413…); only unexpected
        # exceptions are logged with a traceback and turned into a generic 500.
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": "internal server error"}), 500


def create_app() -> Flask:
    # Templates and static assets live at the project root, one level up.
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = get_or_create_secret()
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Enable if you terminate TLS in front of the app:
        SESSION_COOKIE_SECURE=False,
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    )

    register_template_helpers(app)
    register_blueprints(app)
    _configure_logging(app)

    # Security: same-origin CSRF check, optional auth gate, hardened headers.
    app.before_request(check_csrf)
    app.before_request(check_auth)
    app.after_request(add_security_headers)

    init_db()
    return app
