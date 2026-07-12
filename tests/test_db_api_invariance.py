"""API-invariance guard for the database.py mixin split (Phase 6).

The refactor moves Database methods into db/ domain mixins that Database
inherits. Behavior and the public surface must not change. This test asserts
the current Database class still exposes exactly the golden set of methods
captured before the split. If it fails after a move, a method was lost or
renamed; if you add/remove a method on purpose, regenerate the golden file.
"""

import inspect

from tests._db_api_golden import DATABASE_API


def test_database_public_api_is_unchanged():
    import database

    current = {
        name
        for name, value in inspect.getmembers(database.Database, predicate=inspect.isfunction)
    }
    missing = DATABASE_API - current
    added = current - DATABASE_API
    assert not missing, f"Database methods disappeared during refactor: {sorted(missing)}"
    # Added methods are allowed (new helpers), but surface them for awareness.
    assert not added or all(a.startswith("_") for a in added), (
        f"unexpected new PUBLIC Database methods: {sorted(a for a in added if not a.startswith('_'))}"
    )
