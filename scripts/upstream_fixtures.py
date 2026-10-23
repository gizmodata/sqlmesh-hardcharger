"""Connection bridge for SQLMesh's unmodified DuckDB test assertions."""

from __future__ import annotations

import os

import hardcharger
import pytest

from sqlmesh_hardcharger import HardchargerConnectionConfig, HardchargerEngineAdapter


class DuckConnection:
    """Expose DuckDB's convenience methods over the real remote ADBC connection.

    Upstream assertions use conn.execute(...).fetchall()/fetchdf() and extension
    helpers. SQLMesh itself still receives the native DB-API connection.
    """

    def __init__(self, connection):
        self.connection = connection
        self.cursors = []
        self.adapters = []

    def execute(self, sql):
        cursor = self.connection.cursor()
        self.cursors.append(cursor)
        cursor.execute(sql)
        self.connection.commit()
        self.cursor = cursor
        return self

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchdf(self):
        return self.cursor.fetch_arrow_table().to_pandas(date_as_object=False)

    def install_extension(self, extension):
        self.execute(f"INSTALL {extension}")

    def load_extension(self, extension):
        self.execute(f"LOAD {extension}")

    def close(self):
        for cursor in self.cursors:
            cursor.close()
        for adapter in self.adapters:
            adapter.close()
        self.connection.close()


@pytest.fixture
def duck_conn(tmp_path):
    from adbc_driver_hardcharger import dbapi

    with hardcharger.Server(
        extra_args=[
            "--init-sql-commands",
            f"SET secret_directory='{tmp_path}/secrets'",
        ]
    ) as server:
        connection = dbapi.connect(
            uri=server.uri, username=server.username, password=server.password, autocommit=False
        )
        wrapper = DuckConnection(connection)
        try:
            yield wrapper
        finally:
            wrapper.close()


@pytest.fixture
def create_engine_adapter():
    adapters = []

    def create(engine_name, gateway):
        assert engine_name == "duckdb"
        config = HardchargerConnectionConfig(
            host=os.environ["HARDCHARGER_UPSTREAM_HOST"],
            port=int(os.environ["HARDCHARGER_UPSTREAM_PORT"]),
            username=os.environ["HARDCHARGER_UPSTREAM_USERNAME"],
            password=os.environ["HARDCHARGER_UPSTREAM_PASSWORD"],
            use_encryption=False,
            database="memory",
        )
        adapter = config.create_engine_adapter()
        adapter.DEFAULT_BATCH_SIZE = 1
        adapters.append(adapter)
        return adapter

    yield create
    for adapter in adapters:
        adapter.close()


def pytest_collection_modifyitems(items):
    # The upstream unit module's adapter fixture is declared in the module,
    # so substitute its adapter factory while preserving every test assertion.
    for item in items:
        if item.module.__name__.endswith("engine_adapter.test_duckdb"):
            item.module.DuckDBEngineAdapter = BridgedEngineAdapter


class BridgedEngineAdapter(HardchargerEngineAdapter):
    def __init__(self, factory, **kwargs):
        def connect():
            connection = factory()
            if isinstance(connection, DuckConnection) and self not in connection.adapters:
                connection.adapters.append(self)
            return connection.connection if isinstance(connection, DuckConnection) else connection

        super().__init__(connect, **kwargs)
