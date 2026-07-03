"""Characterization tests: export, import, reset."""
import io


def test_export_returns_sqlite_file(client, make_item):
    make_item(name="Exported Machine")
    r = client.get("/api/export")
    assert r.status_code == 200
    assert r.data[:16] == b"SQLite format 3\x00"


def test_import_roundtrip(client, make_item):
    # Snapshot a DB that contains one item, then wipe and restore it.
    make_item(name="Restore Me")
    exported = client.get("/api/export").data

    client.post("/api/reset")
    tree = client.get("/api/tree").get_json()
    assert all(not c["items"] for c in tree)  # empty after reset

    r = client.post("/api/import",
                    data={"db": (io.BytesIO(exported), "rcdb.db")},
                    content_type="multipart/form-data")
    assert r.status_code == 200
    tree = client.get("/api/tree").get_json()
    names = [i["name"] for c in tree for i in c["items"]]
    assert "Restore Me" in names


def test_import_rejects_non_sqlite(client):
    r = client.post("/api/import",
                    data={"db": (io.BytesIO(b"not a database"), "x.db")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_reset_restores_default_categories(client, make_item):
    make_item(name="Temp")
    client.post("/api/categories", json={"name": "Extra"})
    assert client.post("/api/reset").status_code == 200
    cats = client.get("/api/categories").get_json()
    assert set(cats) == {"Desktops", "Laptops", "Hardware", "Manuals"}
