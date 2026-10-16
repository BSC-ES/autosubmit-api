import os
from typing import Tuple
from unittest.mock import MagicMock

import pytest
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

from autosubmit_api.config.basicConfig import APIBasicConfig
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


class TestMaxSqlParams:
    @pytest.mark.parametrize(
        "backend, expected",
        [
            ("sqlite", common.SQLITE_MAX_PARAMS),
            ("postgres", common.POSTGRESQL_MAX_PARAMS),
        ],
    )
    def test_known_backends(self, backend: str, expected: int):
        assert common.max_sql_params(backend) == expected

    @pytest.mark.parametrize("backend", [None, "", "mysql"])
    def test_unknown_backends_use_the_lowest_limit(self, backend: str | None):
        """A smaller chunk is always safe, a bigger one is not."""
        assert common.max_sql_params(backend) == common.SQLITE_MAX_PARAMS

    @pytest.mark.parametrize(
        "configured_backend, expected",
        [
            ("postgres", common.POSTGRESQL_MAX_PARAMS),
            ("sqlite", common.SQLITE_MAX_PARAMS),
        ],
    )
    def test_defaults_to_the_configured_backend(
        self,
        monkeypatch: pytest.MonkeyPatch,
        configured_backend: str,
        expected: int,
    ):
        monkeypatch.setattr(APIBasicConfig, "DATABASE_BACKEND", configured_backend)

        assert common.max_sql_params() == expected


class TestIterParamChunks:
    def test_no_values_yields_no_chunks(self):
        assert list(common.iter_param_chunks([])) == []

    def test_values_that_fit_in_one_query_are_not_split(self):
        values = ["job_a", "job_b", "job_c"]

        assert list(common.iter_param_chunks(values, backend="sqlite")) == [values]

    @pytest.mark.parametrize("backend", ["sqlite", "postgres"])
    def test_every_chunk_fits_in_a_single_query(self, backend: str):
        limit = common.max_sql_params(backend)
        values = list(range(limit + 10))

        chunks = list(common.iter_param_chunks(values, backend=backend))

        assert [len(chunk) for chunk in chunks] == [limit, 10]

    def test_chunks_preserve_the_order_and_every_value(self):
        values = [f"job_{number}" for number in range(2500)]

        chunks = list(common.iter_param_chunks(values, backend="sqlite"))

        assert [len(chunk) for chunk in chunks] == [999, 999, 502]
        assert [value for chunk in chunks for value in chunk] == values
