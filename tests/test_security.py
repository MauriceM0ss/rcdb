"""Tests for the hardening controls added in the security step."""
from conftest import upload


# ── Response headers ───────────────────────────────────────────────────────
def test_security_headers_present(client):
    r = client.get("/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "default-src 'self'" in r.headers.get("Content-Security-Policy", "")


# ── CSRF (same-origin enforcement) ─────────────────────────────────────────
def test_cross_origin_post_blocked(client):
    r = client.post("/api/item", json={"name": "x"},
                    headers={"Origin": "http://evil.example"})
    assert r.status_code == 403


def test_same_origin_post_allowed(client):
    r = client.post("/api/item", json={"name": "ok"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200


def test_headerless_post_allowed(client):
    # No Origin/Referer (curl, native apps, tests) is permitted.
    assert client.post("/api/item", json={"name": "cli"}).status_code == 200


def test_cross_origin_referer_blocked(client):
    r = client.post("/api/item", json={"name": "x"},
                    headers={"Referer": "http://evil.example/page"})
    assert r.status_code == 403


# ── Upload MIME neutralisation (stored XSS defence) ────────────────────────
def test_svg_photo_not_served_inline(client, make_item):
    iid = make_item()
    # Attacker uploads a script-bearing SVG labelled as an image.
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    upload(client, f"/api/photo/{iid}", "photo", "x.svg", svg, "image/svg+xml")
    r = client.get(f"/api/photo/{iid}")
    assert r.status_code == 200
    # Served as a download, never as inline SVG/HTML.
    assert "image/svg" not in r.headers.get("Content-Type", "")
    assert r.headers.get("Content-Type", "").startswith("application/octet-stream")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_png_photo_still_inline(client, make_item):
    from conftest import png_bytes
    iid = make_item()
    upload(client, f"/api/photo/{iid}", "photo", "c.png", png_bytes(), "image/png")
    r = client.get(f"/api/photo/{iid}")
    assert r.headers["Content-Type"].startswith("image/png")


def test_manual_html_text_served_as_plain(client, make_item):
    iid = make_item(category="Manuals")
    html = b"<script>alert(document.domain)</script>"
    # Allowed extension (.txt) but attacker sets an HTML content type.
    fid = upload(client, f"/api/manual-file/{iid}", "file", "note.txt",
                 html, "text/html").get_json()["id"]
    r = client.get(f"/api/manual-file-view/{fid}")
    assert r.status_code == 200
    ct = r.headers.get("Content-Type", "")
    assert ct.startswith("text/plain")   # never text/html
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


# ── Upload size cap ────────────────────────────────────────────────────────
def test_oversized_upload_rejected(client_factory, make_item):
    client = client_factory(RCDB_MAX_UPLOAD_MB="1")
    iid = client.post("/api/item", json={"name": "Big"}).get_json()["item_id"]
    big = b"\x00" * (2 * 1024 * 1024)  # 2 MB > 1 MB cap
    r = upload(client, f"/api/photo/{iid}", "photo", "big.png", big, "image/png")
    assert r.status_code == 413


# ── Optional auth ──────────────────────────────────────────────────────────
def test_auth_disabled_by_default(client):
    assert client.get("/").status_code == 200


def test_auth_gate_blocks_when_enabled(client_factory):
    client = client_factory(RCDB_PASSWORD="hunter2")
    # HTML pages redirect to the login form …
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    # … API calls get a hard 401.
    assert client.get("/api/categories").status_code == 401


def test_login_success_and_logout(client_factory):
    client = client_factory(RCDB_PASSWORD="hunter2")
    bad = client.post("/login", data={"password": "wrong"})
    assert bad.status_code == 401
    ok = client.post("/login", data={"password": "hunter2"})
    assert ok.status_code == 302
    assert client.get("/api/categories").status_code == 200
    client.post("/logout")
    assert client.get("/api/categories").status_code == 401


def test_login_lockout(client_factory):
    client = client_factory(RCDB_PASSWORD="hunter2")
    for _ in range(5):
        client.post("/login", data={"password": "nope"})
    # Even the correct password is refused while locked out.
    r = client.post("/login", data={"password": "hunter2"})
    assert r.status_code == 401
    assert "Too many attempts" in r.get_data(as_text=True)


def test_healthz_exempt_from_auth(client_factory):
    client = client_factory(RCDB_PASSWORD="hunter2")
    # /healthz must answer without a session so container health checks work.
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
