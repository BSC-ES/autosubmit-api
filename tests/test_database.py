import os
from typing import Tuple
from unittest.mock import MagicMock

from sqlalchemy import (
    Column,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)

from autosubmit_api.database import common, tables


def count_pid_lsof(pid):
    openfiles = os.popen(f"lsof -p {pid} | grep db").read()
    print(openfiles)
    return len([x for x in openfiles.strip("\n ").split("\n") if len(x.strip()) > 0])


class TestDatabase:
    def test_open_files(self, fixture_sqlite):
        current_pid = os.getpid()

        counter = count_pid_lsof(current_pid)

        engine = common.create_autosubmit_db_engine()

        assert counter == count_pid_lsof(current_pid)

        with engine.connect() as conn:
            conn.execute(select(tables.ExperimentTable))
            assert counter + 1 == count_pid_lsof(current_pid)

        assert counter == count_pid_lsof(current_pid)


class TestExecuteUpsert:
    def test_insert_new_row(self, fixture_dummy_db: Tuple[Engine, Table]):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            rowcount = common.execute_upsert(
                conn, table, {"id": 1, "name": "alpha", "value": "v1"}, ["id"]
            )
            conn.commit()
            assert rowcount == 1
            row = conn.execute(select(table).where(table.c.id == 1)).first()
        assert row.name == "alpha"
        assert row.value == "v1"

    def test_update_on_conflict(self, fixture_dummy_db: Tuple[Engine, Table]):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            common.execute_upsert(
                conn, table, {"id": 1, "name": "alpha", "value": "v1"}, ["id"]
            )
            conn.commit()
            # Upsert same id with different values
            common.execute_upsert(
                conn, table, {"id": 1, "name": "beta", "value": "v2"}, ["id"]
            )
            conn.commit()
            row = conn.execute(select(table).where(table.c.id == 1)).first()
        assert row.name == "beta"
        assert row.value == "v2"

    def test_update_with_explicit_set(self, fixture_dummy_db: Tuple[Engine, Table]):
        engine, table = fixture_dummy_db

        with engine.connect() as conn:
            common.execute_upsert(
                conn, table, {"id": 1, "name": "alpha", "value": "v1"}, ["id"]
            )
            conn.commit()
            # Only update 'value', leave 'name' unchanged
            common.execute_upsert(
                conn,
                table,
                {"id": 1, "name": "ignored", "value": "v2"},
                ["id"],
                set_={"value": "v2"},
            )
            conn.commit()
            row = conn.execute(select(table).where(table.c.id == 1)).first()
        assert row.name == "alpha"
        assert row.value == "v2"

    def test_insert_does_not_affect_other_rows(
        self, fixture_dummy_db: Tuple[Engine, Table]
    ):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            common.execute_upsert(
                conn, table, {"id": 1, "name": "alpha", "value": "v1"}, ["id"]
            )
            common.execute_upsert(
                conn, table, {"id": 2, "name": "beta", "value": "v2"}, ["id"]
            )
            conn.commit()
            rows = conn.execute(select(table)).all()
        assert len(rows) == 2

    def test_index_elements_as_multiple_types(
        self, fixture_dummy_db: Tuple[Engine, Table]
    ):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            rowcount = common.execute_upsert(
                conn,
                table,
                {"id": 1, "name": "alpha", "value": "v1"},
                [table.c.id],
            )
            conn.commit()
            assert rowcount == 1

            rowcount = common.execute_upsert(
                conn,
                table,
                {"id": 1, "name": "alpha", "value": "v2"},
                ["id"],
            )
            conn.commit()
            assert rowcount == 1
            row = conn.execute(select(table).where(table.c.id == 1)).first()
            assert row.value == "v2"

    def test_fallback_dialect_insert_update(
        self, fixture_dummy_db: Tuple[Engine, Table]
    ):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            # Mock to not use the SQLite dialect and force fallback logic
            mock_conn = MagicMock(wraps=conn)
            mock_conn.dialect = MagicMock(name="unsupported")
            mock_conn.dialect.name = "unsupported"
            rowcount = common.execute_upsert(
                mock_conn, table, {"id": 1, "name": "alpha", "value": "v1"}, ["id"]
            )
            conn.commit()
            assert rowcount == 1
            row = conn.execute(select(table).where(table.c.id == 1)).first()
            assert row.name == "alpha"
            assert row.value == "v1"

            # Upsert same id with different values, should perform an update
            rowcount = common.execute_upsert(
                mock_conn, table, {"id": 1, "name": "beta", "value": "v2"}, ["id"]
            )
            conn.commit()
            assert rowcount == 1
            row = conn.execute(select(table).where(table.c.id == 1)).first()
            assert row.name == "beta"
            assert row.value == "v2"

    def test_rollback_on_exception(self, fixture_dummy_db: Tuple[Engine, Table]):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            # Attempt upsert with invalid data to trigger an exception
            try:
                common.execute_upsert(
                    conn,
                    table,
                    {"id": None, "name": None, "value": "v1"},  # NULL invalid values
                    ["id"],
                )
                raise AssertionError("Expected an exception due to NOT NULL constraint")
            except Exception:
                conn.rollback()

            # Verify that no row was inserted
            row = conn.execute(select(table)).first()
            assert row is None

    def test_fallback_dialect_rollback_on_exception(
        self, fixture_dummy_db: Tuple[Engine, Table]
    ):
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            # Mock to not use the SQLite dialect and force fallback logic
            mock_conn = MagicMock(wraps=conn)
            mock_conn.dialect = MagicMock(name="unsupported")
            mock_conn.dialect.name = "unsupported"

            # Attempt upsert with invalid data to trigger an exception
            try:
                common.execute_upsert(
                    mock_conn,
                    table,
                    {"id": None, "name": None, "value": "v1"},  # NULL invalid values
                    ["id"],
                )
                raise AssertionError("Expected an exception due to NOT NULL constraint")
            except Exception:
                conn.rollback()

            # Verify that no row was inserted
            row = conn.execute(select(table)).first()
            assert row is None

    def upsert_row_on_legacy_table_without_unique_constraint(self):
        """
        Regression test for the hubs: the as_times.db ``experiment_status``
        tables deployed may not have a PRIMARY KEY/UNIQUE constraint on ``exp_id``
        so a native ``ON CONFLICT`` clause would raise.
        ``upsert_row`` must fall back to a schema-agnostic DELETE+INSERT on
        SQLite and native upsert on PostgreSQL.
        """
        engine = create_engine("sqlite:///:memory:")
        meta = MetaData()
        legacy_table = Table(
            "experiment_status",
            meta,
            Column("exp_id", Integer, nullable=False),
            Column("name", String, nullable=False),
            Column("status", String, nullable=False),
            Column("seconds_diff", Integer, nullable=False),
            Column("modified", String, nullable=False),
        )
        meta.create_all(engine)

        values = {
            "exp_id": 1,
            "name": "t000",
            "status": "RUNNING",
            "seconds_diff": 0,
            "modified": "2026-09-01-14:54:53+02:00",
        }
        with engine.connect() as conn:
            rowcount = common.upsert_or_replace(conn, legacy_table, values, ["exp_id"])
            conn.commit()
            assert rowcount == 1

            # Same exp_id again must replace the existing row, not raise nor duplicate
            values["status"] = "NOT_RUNNING"
            rowcount = common.upsert_or_replace(conn, legacy_table, values, ["exp_id"])
            conn.commit()
            assert rowcount == 1
            rows = conn.execute(select(legacy_table)).all()

        assert len(rows) == 1
        assert rows[0].status == "NOT_RUNNING"

    def test_upsert_row_inserts_and_replaces(
        self, fixture_dummy_db: Tuple[Engine, Table]
    ):
        """
        ``upsert_row`` must insert a new row if it does not exist, and replace the existing row if it does.
        Tested on a dummy table with a PRIMARY KEY on ``id``.
        """
        engine, table = fixture_dummy_db
        with engine.connect() as conn:
            # Insert a new row
            rowcount = common.upsert_or_replace(
                conn, table, {"id": 1, "name": "alpha", "value": "v1"}, ["id"]
            )
            conn.commit()
            assert rowcount == 1

            # Replace the existing row with the same id
            rowcount = common.upsert_or_replace(
                conn, table, {"id": 1, "name": "beta", "value": "v2"}, ["id"]
            )
            conn.commit()
            assert rowcount == 1
            rows = conn.execute(select(table)).all()

        assert len(rows) == 1
        assert rows[0].name == "beta"
