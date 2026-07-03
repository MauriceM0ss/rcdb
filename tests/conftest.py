"""Shared pytest fixtures.

Each test runs against a fresh, isolated SQLite database in a temp directory.
The app reads ``DB_PATH`` at import time, so we set it *before* importing the
app module and force a clean re-import per test. This fixture is written to
survive the package refactor: it only relies on the ``app`` module exposing a
Flask instance (``app.app``) and an ``init_db`` callable.
"""
import importlib
import io
import sys

import pytest


def _fresh_app(db_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Drop any cached app/package modules so module-level DB_PATH is re-read.
    for name in [m for m in sys.modules if m == "app" or m.startswith("rcdb")]:
        del sys.modules[name]
    app_module = importlib.import_module("app")
    app_module.init_db()
    app_module.app.config.update(TESTING=True)
    return app_module


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    return _fresh_app(tmp_path / "rcdb.db", monkeypatch)


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


@pytest.fixture()
def client_factory(tmp_path, monkeypatch):
    """Build a test client with extra environment (e.g. RCDB_PASSWORD) set."""
    def _make(**env):
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        mod = _fresh_app(tmp_path / "rcdb.db", monkeypatch)
        return mod.app.test_client()
    return _make


@pytest.fixture()
def make_item(client):
    """Create an item and return its item_id."""
    def _make(name="Test Item", category="Desktops", hardware_type=""):
        r = client.post("/api/item", json={
            "name": name, "category": category, "hardware_type": hardware_type})
        assert r.status_code == 200, r.data
        return r.get_json()["item_id"]
    return _make


def png_bytes():
    """A tiny valid 1x1 PNG."""
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def upload(client, url, field, filename, data, content_type):
    return client.post(
        url,
        data={field: (io.BytesIO(data), filename, content_type)},
        content_type="multipart/form-data",
    )
