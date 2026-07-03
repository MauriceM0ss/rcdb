"""Characterization tests: items, categories, notes, tasks, specs."""


# ── Items ──────────────────────────────────────────────────────────────────
def test_create_item_requires_name(client):
    r = client.post("/api/item", json={"name": "  "})
    assert r.status_code == 400


def test_item_id_is_slugified_and_unique(client, make_item):
    a = make_item(name="IBM PC XT")
    b = make_item(name="IBM PC XT")
    assert a.startswith("ibm_pc_xt_") and b.startswith("ibm_pc_xt_")
    assert a != b  # random suffix keeps them distinct


def test_update_item_field_allowlist(client, make_item):
    iid = make_item()
    ok = client.put(f"/api/item/{iid}", json={"field": "name", "content": "Renamed"})
    assert ok.status_code == 200
    bad = client.put(f"/api/item/{iid}", json={"field": "id", "content": "x"})
    assert bad.status_code == 400


def test_update_item_persists(client, make_item):
    iid = make_item()
    client.put(f"/api/item/{iid}", json={"field": "description", "content": "hello"})
    body = client.get(f"/item/{iid}").get_data(as_text=True)
    assert "hello" in body


def test_delete_item(client, make_item):
    iid = make_item(name="Doomed")
    assert client.delete(f"/api/item/{iid}").status_code == 200
    assert client.get(f"/item/{iid}").status_code == 404


# ── Categories ─────────────────────────────────────────────────────────────
def test_add_category(client):
    assert client.post("/api/categories", json={"name": "Consoles"}).status_code == 200
    assert "Consoles" in client.get("/api/categories").get_json()


def test_add_duplicate_category_conflicts(client):
    client.post("/api/categories", json={"name": "Consoles"})
    assert client.post("/api/categories", json={"name": "Consoles"}).status_code == 409


def test_rename_category_cascades_to_items(client, make_item):
    iid = make_item(name="NES", category="Hardware")
    r = client.put("/api/categories/Hardware", json={"new_name": "Components"})
    assert r.status_code == 200
    # The item moved to the renamed category.
    data = client.get("/api/tree").get_json()
    comp = next(c for c in data if c["category"] == "Components")
    assert any(i["name"] == "NES" for i in comp["items"])


def test_delete_category_reassigns_items(client, make_item):
    client.post("/api/categories", json={"name": "Consoles"})
    iid = make_item(name="Atari", category="Consoles")
    r = client.delete("/api/categories/Consoles")
    assert r.status_code == 200
    fallback = r.get_json()["fallback"]
    data = client.get("/api/tree").get_json()
    target = next(c for c in data if c["category"] == fallback)
    assert any(i["name"] == "Atari" for i in target["items"])


# ── Notes ──────────────────────────────────────────────────────────────────
def test_note_lifecycle(client, make_item):
    iid = make_item()
    nid = client.post(f"/api/note/{iid}", json={"content": "first"}).get_json()["id"]
    assert client.put(f"/api/note/{nid}", json={"content": "edited"}).status_code == 200
    assert client.post(f"/api/note/{iid}", json={"content": ""}).status_code == 400
    assert client.delete(f"/api/note/{nid}").status_code == 200


# ── Tasks ──────────────────────────────────────────────────────────────────
def test_task_lifecycle(client, make_item):
    iid = make_item()
    tid = client.post(f"/api/task/{iid}", json={"text": "restore"}).get_json()["id"]
    assert client.patch(f"/api/task/{tid}", json={"done": True}).status_code == 200
    assert client.post(f"/api/task/{iid}", json={"text": ""}).status_code == 400
    assert client.delete(f"/api/task/{tid}").status_code == 200


# ── Specs ──────────────────────────────────────────────────────────────────
def test_spec_lifecycle(client, make_item):
    iid = make_item()
    sid = client.post(f"/api/spec/{iid}", json={"key": "CPU", "value": "8088"}).get_json()["id"]
    assert client.put(f"/api/spec/{sid}", json={"key": "CPU", "value": "V20"}).status_code == 200
    assert client.post(f"/api/spec/{iid}", json={"key": "", "value": "x"}).status_code == 400
    assert client.delete(f"/api/spec/{sid}").status_code == 200
