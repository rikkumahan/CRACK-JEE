"""
Shared test fixtures for the JEE Performance Engine test suite.

The Python server uses a module-level singleton connection (_default_conn)
against data/jee.db.  Tests that exercise the in-process MCP server must
start with a clean database or they contaminate each other.

This autouse fixture runs before every test:
  1. Closes and nulls the singleton connection (releases Windows file locks).
  2. Deletes data/jee.db if it exists.

Tests that bring their own connection (e.g., test_interventions.py's
`test_db` fixture using tmp_path) are unaffected because they never
touch _default_conn or DEFAULT_DB_PATH.
"""

import gc
from pathlib import Path

import pytest

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jee.db"


@pytest.fixture(autouse=True)
def reset_shared_db():
    """Reset the singleton DB connection and delete jee.db before each test."""
    import db  # imported here so the module is available

    # --- teardown of any previous test ---
    if db._default_conn is not None:
        try:
            db._default_conn.close()
        except Exception:
            pass
        db._default_conn = None

    # Force CPython to release any lingering file handles before we try to delete.
    gc.collect()

    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except OSError:
            pass  # If another process holds it, the test will fail on its own terms.

    yield
    # No post-test teardown needed; the next test's setup phase handles it.

