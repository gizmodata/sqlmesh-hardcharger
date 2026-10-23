"""Shared fixtures for integration tests.

The Hardcharger server is started as a managed subprocess via the
[`hardcharger`](https://pypi.org/project/hardcharger/) PyPI package — Docker is
no longer required for the server itself. PostgreSQL is still expected
to be reachable at ``$POSTGRES_HOST:$POSTGRES_PORT`` for the DuckLake
tests; ``docker compose -f tests/integration/docker/compose.hardcharger.yaml
up -d`` still brings that up, and CI continues to launch postgres as a
service container.
"""

from __future__ import annotations

import typing as t

import hardcharger
import pytest

from sqlmesh_hardcharger import HardchargerConnectionConfig, HardchargerEngineAdapter


@pytest.fixture(scope="session")
def hardcharger_server(tmp_path_factory) -> t.Generator[hardcharger.Server, None, None]:
    """Start a Hardcharger server as a subprocess for the duration of the
    pytest session. Auto-picks a free port."""
    work = tmp_path_factory.mktemp("hardcharger")
    with hardcharger.Server(
        username="hardcharger_user",
        password="hardcharger_password",
        extra_args=["--init-sql-commands", f"SET secret_directory='{work}/secrets'"],
    ) as srv:
        yield srv


@pytest.fixture(scope="session")
def hardcharger_config(hardcharger_server: hardcharger.Server) -> HardchargerConnectionConfig:
    """Connection config pointing at the test server."""
    return HardchargerConnectionConfig(
        host=hardcharger_server.host,
        port=hardcharger_server.port,
        username=hardcharger_server.username,
        password=hardcharger_server.password,
        use_encryption=False,
    )


@pytest.fixture(scope="session")
def hardcharger_adapter(
    hardcharger_config: HardchargerConnectionConfig,
) -> t.Generator[HardchargerEngineAdapter, None, None]:
    """Engine adapter for the test session."""
    adapter = hardcharger_config.create_engine_adapter()
    yield adapter
    adapter.close()
