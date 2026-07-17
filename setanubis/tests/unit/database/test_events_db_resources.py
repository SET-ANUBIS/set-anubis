"""Resource-lifecycle tests for the current event database manager."""

import sqlite3

import pytest

from SetAnubis.core.DataBase.domain.EventDatabaseManager import EventDatabaseManager


def test_connection_context_closes_connection(tmp_path):
    db = EventDatabaseManager(
        db_path=str(tmp_path / "events.sqlite"),
        storage_dir=str(tmp_path / "storage"),
    )
    with db._conn() as connection:
        connection.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")
