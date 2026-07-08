"""Tests for deterministic_schema_dump.py

Validates that the schema dump tool produces deterministic, sorted output
regardless of the order objects are created in the SQLite database.

Run:
    TEST=true PYTHONPATH="." pytest tools/test_deterministic_schema_dump.py -v
"""

import os
import sqlite3
import tempfile

import pytest

from tools.deterministic_schema_dump import dump_deterministic


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _create_db_with_schema(db_path, ddl):
    """Helper to create a database from DDL statements."""
    conn = sqlite3.connect(db_path)
    conn.executescript(ddl)
    conn.close()


class TestDeterministicSchemaDump:
    def test_tables_sorted_alphabetically(self, temp_db):
        """Tables should be emitted in alphabetical order by name."""
        _create_db_with_schema(
            temp_db,
            """
            CREATE TABLE zebra (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE apple (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE mango (id INTEGER PRIMARY KEY, name TEXT);
            """,
        )
        output = dump_deterministic(temp_db)
        lines = output.strip().split("\n")
        table_lines = [l for l in lines if l.startswith("CREATE TABLE")]
        assert "apple" in table_lines[0]
        assert "mango" in table_lines[1]
        assert "zebra" in table_lines[2]

    def test_indexes_follow_their_table(self, temp_db):
        """Each table's indexes should appear immediately after the table."""
        _create_db_with_schema(
            temp_db,
            """
            CREATE TABLE beta (id INTEGER PRIMARY KEY, name TEXT, value TEXT);
            CREATE INDEX beta_name ON beta (name);
            CREATE INDEX beta_value ON beta (value);
            CREATE TABLE alpha (id INTEGER PRIMARY KEY, code TEXT);
            CREATE INDEX alpha_code ON alpha (code);
            """,
        )
        output = dump_deterministic(temp_db)
        lines = output.strip().split("\n")

        # Find positions
        alpha_table = next(i for i, l in enumerate(lines) if "CREATE TABLE alpha" in l)
        alpha_idx = next(i for i, l in enumerate(lines) if "alpha_code" in l)
        beta_table = next(i for i, l in enumerate(lines) if "CREATE TABLE beta" in l)

        # alpha table comes first (alphabetically), its index follows, then beta
        assert alpha_table < alpha_idx
        assert alpha_idx < beta_table

    def test_indexes_sorted_by_name(self, temp_db):
        """Indexes for a table should be sorted alphabetically by index name."""
        _create_db_with_schema(
            temp_db,
            """
            CREATE TABLE widget (id INTEGER PRIMARY KEY, a TEXT, b TEXT, c TEXT);
            CREATE INDEX widget_c ON widget (c);
            CREATE INDEX widget_a ON widget (a);
            CREATE INDEX widget_b ON widget (b);
            """,
        )
        output = dump_deterministic(temp_db)
        idx_lines = [
            l for l in output.split("\n") if "CREATE INDEX" in l or "CREATE UNIQUE INDEX" in l
        ]
        assert "widget_a" in idx_lines[0]
        assert "widget_b" in idx_lines[1]
        assert "widget_c" in idx_lines[2]

    def test_idempotent_output(self, temp_db):
        """Running dump twice on the same database produces identical output."""
        _create_db_with_schema(
            temp_db,
            """
            CREATE TABLE foo (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE INDEX foo_name ON foo (name);
            CREATE TABLE bar (id INTEGER PRIMARY KEY, value INTEGER);
            CREATE UNIQUE INDEX bar_value ON bar (value);
            """,
        )
        run1 = dump_deterministic(temp_db)
        run2 = dump_deterministic(temp_db)
        assert run1 == run2

    def test_round_trip_idempotent(self, temp_db):
        """Loading the dump into a new DB and re-dumping produces identical output."""
        _create_db_with_schema(
            temp_db,
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL);
            CREATE UNIQUE INDEX users_email ON users (email);
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX posts_user_id ON posts (user_id);
            """,
        )
        dump1 = dump_deterministic(temp_db)

        # Load dump into a new database
        fd2, path2 = tempfile.mkstemp(suffix=".db")
        os.close(fd2)
        try:
            _create_db_with_schema(path2, dump1)
            dump2 = dump_deterministic(path2)
            assert dump1 == dump2
        finally:
            os.unlink(path2)

    def test_excludes_sqlite_sequence(self, temp_db):
        """The sqlite_sequence internal table should not appear in output."""
        _create_db_with_schema(
            temp_db,
            """
            CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
            """,
        )
        # Insert a row to create sqlite_sequence
        conn = sqlite3.connect(temp_db)
        conn.execute("INSERT INTO items (name) VALUES ('test')")
        conn.commit()
        conn.close()

        output = dump_deterministic(temp_db)
        assert "sqlite_sequence" not in output

    def test_insertion_order_does_not_affect_output(self):
        """Different creation orders should produce identical output."""
        ddl_order_a = """
            CREATE TABLE alpha (id INTEGER PRIMARY KEY, x TEXT);
            CREATE INDEX alpha_x ON alpha (x);
            CREATE TABLE beta (id INTEGER PRIMARY KEY, y TEXT);
            CREATE INDEX beta_y ON beta (y);
        """
        ddl_order_b = """
            CREATE TABLE beta (id INTEGER PRIMARY KEY, y TEXT);
            CREATE INDEX beta_y ON beta (y);
            CREATE TABLE alpha (id INTEGER PRIMARY KEY, x TEXT);
            CREATE INDEX alpha_x ON alpha (x);
        """
        fd_a, path_a = tempfile.mkstemp(suffix=".db")
        fd_b, path_b = tempfile.mkstemp(suffix=".db")
        os.close(fd_a)
        os.close(fd_b)
        try:
            _create_db_with_schema(path_a, ddl_order_a)
            _create_db_with_schema(path_b, ddl_order_b)
            assert dump_deterministic(path_a) == dump_deterministic(path_b)
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_real_schema_loads_and_is_idempotent(self):
        """The actual quay_schema.sql file should load and round-trip cleanly."""
        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "internal",
            "dal",
            "schema",
            "sqlite",
            "quay_schema.sql",
        )
        if not os.path.exists(schema_path):
            pytest.skip("quay_schema.sql not found")

        with open(schema_path) as f:
            schema = f.read()

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            _create_db_with_schema(db_path, schema)
            dump1 = dump_deterministic(db_path)

            fd2, db_path2 = tempfile.mkstemp(suffix=".db")
            os.close(fd2)
            try:
                _create_db_with_schema(db_path2, dump1)
                dump2 = dump_deterministic(db_path2)
                assert dump1 == dump2, "Round-trip of real schema is not idempotent"
            finally:
                os.unlink(db_path2)
        finally:
            os.unlink(db_path)
