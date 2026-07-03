"""RCDB entrypoint — thin wrapper around the application factory in ``rcdb/``.

Run directly (``python app.py``) or via a WSGI server pointing at ``app:app``.
``init_db`` is re-exported so the test suite can import it from here.
"""
from rcdb import create_app, init_db  # noqa: F401  (init_db re-exported for tests)

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
