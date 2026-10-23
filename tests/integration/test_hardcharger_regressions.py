"""Real remote-session regressions not covered by the original adapter suite."""

import subprocess
import sys

import pytest
from sqlglot import exp

from sqlmesh_hardcharger import HardchargerConnectionConfig

pytestmark = pytest.mark.integration


def test_default_catalog_applies_to_every_connection(hardcharger_server, hardcharger_adapter):
    hardcharger_adapter.execute("ATTACH IF NOT EXISTS ':memory:' AS configured_catalog")
    config = HardchargerConnectionConfig(
        host=hardcharger_server.host,
        port=hardcharger_server.port,
        username=hardcharger_server.username,
        password=hardcharger_server.password,
        use_encryption=False,
        database="configured_catalog",
    )
    adapter = config.create_engine_adapter()
    try:
        assert adapter.fetchone("SELECT current_database()") == ("configured_catalog",)
    finally:
        adapter.close()


def test_nested_transaction_rolls_back_on_error(hardcharger_adapter):
    adapter = hardcharger_adapter
    adapter.execute("CREATE TABLE rollback_regression(id INT)")
    try:
        with pytest.raises(RuntimeError, match="abort"):
            with adapter.transaction():
                adapter.execute("INSERT INTO rollback_regression VALUES (1)")
                with adapter.transaction():
                    adapter.execute("INSERT INTO rollback_regression VALUES (2)")
                raise RuntimeError("abort")
        assert adapter.fetchall("SELECT * FROM rollback_regression") == []
        adapter.execute("INSERT INTO rollback_regression VALUES (3)")
        assert adapter.fetchall("SELECT * FROM rollback_regression") == [(3,)]
    finally:
        adapter.drop_table("rollback_regression")


def test_dataframe_query_error_does_not_poison_connection(hardcharger_adapter):
    with pytest.raises(Exception, match="does not exist"):
        hardcharger_adapter.fetchdf("SELECT * FROM missing_dataframe_table")
    assert hardcharger_adapter.fetchone("SELECT 42") == (42,)


def test_quoted_schema_names_with_dots(hardcharger_adapter):
    table = exp.to_table('memory."schema.with.dot"."table.with.dot"', dialect="duckdb")
    try:
        hardcharger_adapter.create_table(table, {"id": exp.DataType.build("INT")})
        assert hardcharger_adapter.table_exists(table)
    finally:
        hardcharger_adapter.drop_schema('memory."schema.with.dot"', cascade=True)


def test_yaml_cli_loads_registered_adapter(hardcharger_server, tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models/example.sql").write_text(
        "MODEL (name analytics.example, kind FULL); SELECT 42 AS answer;"
    )
    (tmp_path / "config.yaml").write_text(
        "gateways:\n  hc:\n    connection:\n      type: hardcharger\n"
        f"      host: {hardcharger_server.host}\n      port: {hardcharger_server.port}\n"
        f"      username: {hardcharger_server.username}\n      password: {hardcharger_server.password}\n"
        "      use_encryption: false\n    state_connection:\n      type: duckdb\n"
        "model_defaults:\n  dialect: duckdb\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from sqlmesh_hardcharger.cli import main; main()",
            "--paths",
            str(tmp_path),
            "info",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Data warehouse connection succeeded" in result.stdout
