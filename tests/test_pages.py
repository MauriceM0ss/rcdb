"""Characterization tests: page rendering and read-only API surface."""


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "RCDB" in body
    # Default categories appear in the New Item modal.
    assert "Desktops" in body and "Manuals" in body


def test_index_category_filter(client, make_item):
    make_item(name="Amiga 500", category="Desktops")
    r = client.get("/?cat=Desktops")
    assert r.status_code == 200
    assert "Amiga 500" in r.get_data(as_text=True)


def test_item_detail_renders(client, make_item):
    iid = make_item(name="IBM PC XT")
    r = client.get(f"/item/{iid}")
    assert r.status_code == 200
    assert "IBM PC XT" in r.get_data(as_text=True)


def test_item_detail_404(client):
    assert client.get("/item/does_not_exist").status_code == 404


def test_tree_structure(client, make_item):
    make_item(name="Commodore 64", category="Desktops")
    data = client.get("/api/tree").get_json()
    assert isinstance(data, list)
    cats = {c["category"]: c["items"] for c in data}
    assert "Desktops" in cats
    names = [i["name"] for i in cats["Desktops"]]
    assert "Commodore 64" in names


def test_hardware_templates(client):
    data = client.get("/api/hardware-templates").get_json()
    assert "Hard Drive" in data and "Videocard" in data
    # Structure of a template entry is preserved.
    keys = [f["key"] for f in data["Hard Drive"]]
    assert "Interface" in keys and "Capacity" in keys


def test_list_categories_defaults(client):
    cats = client.get("/api/categories").get_json()
    assert set(cats) == {"Desktops", "Laptops", "Hardware", "Manuals"}


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
