# RCDB — Security Notes

This document records the threat model, the findings from the hardening review,
their status, and operational recommendations. It reflects the state of the
`harden` work on the RCDB codebase.

## Threat model

RCDB is a personal inventory web app. It stores no credentials of value, but it
does accept file uploads (images, manual documents) and serves them back to the
browser, and it exposes a full read/write JSON API. The realistic threats are:

- **Stored XSS** — a malicious or booby-trapped upload executing script in the
  app's origin when later viewed.
- **CSRF** — another site the user has open driving RCDB's state-changing
  endpoints (create/delete items, upload files, or **replace the whole database**
  via import).
- **Resource exhaustion** — oversized uploads filling the disk/volume.
- **Unauthorised access** — anyone able to reach the port has full control.

The assumed deployment is a **trusted home/LAN network** behind Docker. The app
is not intended to be exposed directly to the internet; see recommendations.

## Findings & status

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | **Stored XSS via attacker-controlled MIME type.** Uploaded photos/gallery/manual files stored the browser-supplied `Content-Type` and served it back inline, so an SVG-with-script or an HTML file relabelled as an image/text could execute JS in the app origin. | High | **Fixed** |
| 2 | **CSRF on state-changing endpoints**, notably the multipart upload routes and `/api/import` (which replaces the entire DB). | High | **Fixed** |
| 3 | **No upload size limit** (`MAX_CONTENT_LENGTH` unset) → disk/volume-fill DoS. | Medium | **Fixed** |
| 4 | **No authentication** — full CRUD open to anyone who can reach the port. | Medium | **Mitigated** (optional) |
| 5 | **Missing security headers** (no `nosniff`, framing, referrer, or CSP). | Low–Med | **Fixed** |
| 6 | **Import accepts any SQLite file** and replaces the live DB. | Low | **Accepted** |
| 7 | **Flask development server** used to serve the app. | Low | **Accepted** |
| 8 | **CSP allows `'unsafe-inline'` scripts** (templates rely on inline JS). | Low | **Accepted** |

### How each was addressed

**1 — Stored XSS (fixed).** Serving is now neutralised at egress
(`rcdb/security.py`):
- All responses carry `X-Content-Type-Options: nosniff`, so the browser never
  re-sniffs a payload into an executable type.
- Images are served inline **only** for an allow-list of raster types
  (`png/jpeg/gif/webp/bmp/ico/tiff`). Anything else — including `image/svg+xml`
  — is forced to a download. A lie such as an SVG labelled `image/png` is served
  as `image/png` with `nosniff`, so it decodes as a broken image, never as SVG.
- Manual files are served with a type derived from their (allow-listed)
  **extension**, not the stored client MIME: `.pdf` inline as `application/pdf`,
  `.txt`/`.md` inline as `text/plain`, everything else as a download. `text/html`
  is therefore never emitted. Tests: `test_svg_photo_not_served_inline`,
  `test_manual_html_text_served_as_plain`.

**2 — CSRF (fixed).** A `before_request` same-origin check (`check_csrf`) rejects
any unsafe-method request (`POST/PUT/PATCH/DELETE`) whose `Origin` or `Referer`
header is present and cross-origin. Browsers always attach `Origin` to
cross-site state-changing requests (including auto-submitting multipart forms),
so this blocks the CSRF path to uploads and to `/api/import`. Header-less clients
(curl, native tooling, tests) are allowed through, so the JSON API remains
scriptable on the trusted network. `SESSION_COOKIE_SAMESITE=Lax` adds defence in
depth. Tests: `test_cross_origin_post_blocked`, `test_cross_origin_referer_blocked`.

**3 — Upload size limit (fixed).** `MAX_CONTENT_LENGTH` defaults to **64 MB**
(override with `RCDB_MAX_UPLOAD_MB`). Oversized requests get `413`. Test:
`test_oversized_upload_rejected`.

**4 — Authentication (optional).** Off by default (unchanged LAN behaviour).
Setting **`RCDB_PASSWORD`** enables a session-cookie login gate: HTML pages
redirect to `/login`, API calls return `401`. Passwords are compared in constant
time; there is a per-IP lockout (5 failures / 5 minutes). `/healthz` is exempt so
container health checks work without credentials. Tests: `test_auth_*`.

**5 — Security headers (fixed).** Every response sets `X-Content-Type-Options`,
`X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: same-origin`, and a
`Content-Security-Policy` restricting `default-src` to `'self'` (plus Google
Fonts and the inline scripts/styles the templates need; `object-src 'none'`,
`base-uri 'self'`, `frame-ancestors 'self'`).

**6 — Import replaces the DB (accepted).** This is the intended restore feature.
It is now protected by the CSRF check and (optionally) auth, and it validates the
SQLite magic bytes and that the file opens. Keep backups before importing.

**7 — Dev server (accepted).** Acceptable for personal LAN use. For anything
internet-facing, run behind a reverse proxy (TLS) or a production WSGI server
(e.g. `gunicorn 'app:app'`) and set `SESSION_COOKIE_SECURE=True`.

**8 — `'unsafe-inline'` scripts (accepted).** The templates use inline JavaScript,
so the CSP cannot forbid inline scripts without a larger refactor (external JS +
nonces). The primary XSS control is the MIME neutralisation in finding 1; the CSP
is defence in depth (`object-src 'none'`, framing and base-uri locked down).

## SQL injection

All queries use parameterised placeholders. The two f-string queries are safe:
`UPDATE items SET {field}=?` validates `field` against a fixed allow-list, and the
bulk delete/reset statements interpolate only hard-coded table-name literals.

## Operational recommendations

- **Do not expose RCDB directly to the internet.** Keep it on a trusted network,
  or front it with a reverse proxy that adds TLS and (ideally) its own auth.
- If you must expose it, set `RCDB_PASSWORD`, terminate TLS in front, and set
  `SESSION_COOKIE_SECURE=True` in `rcdb/__init__.py`.
- **Back up the volume regularly** (see README → *Back up & restore*). Always
  export/copy the DB before using Import.
- Keep the base image and `flask` pinned and rebuild periodically for patches.

## Reporting

This is a personal project. Note issues in the repository's tracker.
