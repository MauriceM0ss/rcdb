"""Security controls: response neutralisation, headers, CSRF and optional auth.

Design notes
------------
* Uploaded photos and manual files are served back to the browser. The stored
  MIME type is attacker-controlled, so we never let the browser *sniff* content
  (``X-Content-Type-Options: nosniff``) and we only ever serve a small allow-list
  of types inline. Anything else is forced to a download, so an SVG or HTML file
  masquerading as an image can never execute script in the app's origin.
* CSRF: browsers attach an ``Origin`` header to every state-changing request
  (including cross-site auto-submitting forms, which is how the multipart upload
  and ``/api/import`` endpoints could otherwise be abused). We reject a mutating
  request whose ``Origin``/``Referer`` is present and cross-origin. Header-less
  clients (curl, native apps, tests) are allowed through.
* Auth is optional and off by default. Setting ``RCDB_PASSWORD`` turns on a
  session gate with a simple per-IP lockout.
"""
import io
import os
import time
from urllib.parse import urlparse

from flask import (
    abort,
    redirect,
    request,
    send_file,
    session,
    url_for,
)

from .config import AUTH_PASSWORD

# ── Content neutralisation ─────────────────────────────────────────────────
# Raster image types safe to render inline. SVG is deliberately excluded (it
# can carry <script>); it will be served as a download instead.
SAFE_INLINE_IMAGE_MIMES = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "image/bmp", "image/x-icon", "image/tiff",
}

# Manual attachments are served with a type derived from their (allow-listed)
# extension — never from the stored client MIME. Types not listed here download.
MANUAL_INLINE_MIMES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".md":  "text/plain; charset=utf-8",
}


def safe_image_response(data: bytes, stored_mime: str):
    """Serve an image inline only if its type is a known-safe raster format."""
    if stored_mime in SAFE_INLINE_IMAGE_MIMES:
        return send_file(io.BytesIO(data), mimetype=stored_mime)
    return send_file(io.BytesIO(data), mimetype="application/octet-stream",
                     as_attachment=True, download_name="download")


def _manual_mime(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    return MANUAL_INLINE_MIMES.get(ext)


def safe_manual_view_response(filename: str, data: bytes):
    """Inline-view a manual file using an extension-derived, script-free type."""
    inline_mime = _manual_mime(filename)
    if inline_mime:
        return send_file(io.BytesIO(data), mimetype=inline_mime, download_name=filename)
    return send_file(io.BytesIO(data), mimetype="application/octet-stream",
                     as_attachment=True, download_name=filename)


def safe_manual_download_response(filename: str, data: bytes):
    """Download a manual file with a safe content type."""
    mime = (_manual_mime(filename) or "application/octet-stream").split(";")[0]
    return send_file(io.BytesIO(data), mimetype=mime,
                     as_attachment=True, download_name=filename)


# ── Response headers ───────────────────────────────────────────────────────
# `marked` is not loaded from a CDN and the only external assets are Google
# Fonts, so the CSP can stay tight apart from the inline scripts/styles the
# templates rely on.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "object-src 'none'; base-uri 'self'; frame-ancestors 'self' http://localhost:5173 tauri://localhost; "
    "frame-src 'self'; "
    "form-action 'self'"
)


def add_security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Content-Security-Policy", _CSP)
    return resp


# ── CSRF (same-origin) ─────────────────────────────────────────────────────
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def check_csrf():
    if request.method in _SAFE_METHODS:
        return
    for header in ("Origin", "Referer"):
        val = request.headers.get(header)
        if val:
            if urlparse(val).netloc != request.host:
                abort(403, description="Cross-origin request blocked")
            return  # present and same-origin → accept
    # Neither header present: not a browser form/fetch — allow (API clients).


# ── Optional password auth ─────────────────────────────────────────────────
_LOCK_THRESHOLD = 5      # failed attempts …
_LOCK_WINDOW = 300       # … within this many seconds triggers a lockout
_fails: dict[str, list[float]] = {}


def auth_enabled() -> bool:
    return bool(AUTH_PASSWORD)


def _recent_fails(ip: str) -> int:
    now = time.time()
    hits = [t for t in _fails.get(ip, []) if now - t < _LOCK_WINDOW]
    _fails[ip] = hits
    return len(hits)


def is_locked(ip: str) -> bool:
    return _recent_fails(ip) >= _LOCK_THRESHOLD


def record_failure(ip: str) -> None:
    _fails.setdefault(ip, []).append(time.time())


def clear_failures(ip: str) -> None:
    _fails.pop(ip, None)


# Endpoints reachable without a session when auth is on.
_AUTH_EXEMPT_ENDPOINTS = {"auth.login", "auth.logout", "static"}
_AUTH_EXEMPT_PATHS = {"/healthz"}


def check_auth():
    if not AUTH_PASSWORD or session.get("authed"):
        return
    if request.endpoint in _AUTH_EXEMPT_ENDPOINTS or request.path in _AUTH_EXEMPT_PATHS:
        return
    if request.path.startswith("/api/"):
        abort(401, description="Authentication required")
    return redirect(url_for("auth.login", next=request.path))
