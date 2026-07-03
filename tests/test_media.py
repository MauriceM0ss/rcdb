"""Characterization tests: photos, gallery photos, manual files, links."""
from conftest import png_bytes, upload


# ── Cover photo ────────────────────────────────────────────────────────────
def test_photo_upload_get_delete(client, make_item):
    iid = make_item()
    assert upload(client, f"/api/photo/{iid}", "photo", "c.png",
                  png_bytes(), "image/png").status_code == 200
    g = client.get(f"/api/photo/{iid}")
    assert g.status_code == 200
    assert g.data == png_bytes()
    assert client.delete(f"/api/photo/{iid}").status_code == 200
    assert client.get(f"/api/photo/{iid}").status_code == 404


def test_photo_missing_file_field(client, make_item):
    iid = make_item()
    assert client.post(f"/api/photo/{iid}", data={}).status_code == 400


# ── Gallery ────────────────────────────────────────────────────────────────
def test_gallery_upload_get_delete(client, make_item):
    iid = make_item()
    pid = upload(client, f"/api/gallery/{iid}", "photo", "g.png",
                 png_bytes(), "image/png").get_json()["id"]
    assert client.get(f"/api/gallery-photo/{pid}").status_code == 200
    assert client.delete(f"/api/gallery-photo/{pid}").status_code == 200
    assert client.get(f"/api/gallery-photo/{pid}").status_code == 404


# ── Manual files ───────────────────────────────────────────────────────────
def test_manual_file_allowed_extension(client, make_item):
    iid = make_item(category="Manuals")
    r = upload(client, f"/api/manual-file/{iid}", "file", "guide.txt",
               b"hello manual", "text/plain")
    assert r.status_code == 200
    fid = r.get_json()["id"]
    # Listed
    listed = client.get(f"/api/manual-files/{iid}").get_json()
    assert any(f["id"] == fid for f in listed)
    # Downloadable (attachment) and viewable (inline)
    assert client.get(f"/api/manual-file/{fid}").status_code == 200
    assert client.get(f"/api/manual-file-view/{fid}").status_code == 200
    assert client.delete(f"/api/manual-file/{fid}").status_code == 200


def test_manual_file_rejects_disallowed_extension(client, make_item):
    iid = make_item(category="Manuals")
    r = upload(client, f"/api/manual-file/{iid}", "file", "evil.exe",
               b"MZ", "application/octet-stream")
    assert r.status_code == 400


# ── Item ↔ manual links ────────────────────────────────────────────────────
def test_manual_link_unlink(client, make_item):
    machine = make_item(name="PC", category="Desktops")
    manual = make_item(name="PC Manual", category="Manuals")
    link_id = client.post(f"/api/item-manuals/{machine}",
                          json={"manual_id": manual}).get_json()["id"]
    # Duplicate link conflicts.
    assert client.post(f"/api/item-manuals/{machine}",
                       json={"manual_id": manual}).status_code == 409
    assert client.delete(f"/api/item-manuals/{link_id}").status_code == 200
