# SQLMesh Hardcharger Adapter

![Hardcharger](https://raw.githubusercontent.com/gizmodata/sqlmesh-hardcharger/main/docs/assets/hardcharger-banner-dark.png)

[![CI](https://github.com/gizmodata/sqlmesh-hardcharger/actions/workflows/ci.yml/badge.svg)](https://github.com/gizmodata/sqlmesh-hardcharger/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlmesh-hardcharger)](https://pypi.org/project/sqlmesh-hardcharger/)
[![Python](https://img.shields.io/pypi/pyversions/sqlmesh-hardcharger)](https://pypi.org/project/sqlmesh-hardcharger/)

Run [SQLMesh](https://sqlmesh.com) transformations on [Hardcharger™](https://gizmodata.com/hardcharger), GizmoData's DuckDB 2.0 server. Connect using the native [Hardcharger ADBC driver](https://github.com/gizmodata/hardcharger-adbc) over **Warp SQL HTTP(S)**.

## Install

```bash
pip install sqlmesh-hardcharger
```

Python **3.11 or later**. Installs SQLMesh 0.236.4 (compatible 0.236.x releases) and `adbc-driver-hardcharger>=2.0.2,<3`. SQLGlot stays within SQLMesh's supported 30.8.x range. The local DuckDB package is SQLMesh's dependency; remote queries execute on the Hardcharger server's DuckDB 2.0 engine.

## Quick start

Add `config.yaml` to your SQLMesh project:

```yaml
gateways:
  hardcharger:
    connection:
      type: hardcharger
      host: localhost
      port: 31337
      username: "{{ env_var('HARDCHARGER_USERNAME') }}"
      password: "{{ env_var('HARDCHARGER_PASSWORD') }}"
      use_encryption: true
      # database: analytics  # optional existing default catalog
    state_connection:
      type: duckdb
      database: sqlmesh_state.duckdb

default_gateway: hardcharger
model_defaults:
  dialect: duckdb
```

Use the included CLI, which registers the adapter **before** SQLMesh loads YAML:

```bash
sqlmesh-hardcharger info
sqlmesh-hardcharger plan
sqlmesh-hardcharger run
```

It exposes SQLMesh's standard commands and options. For a local server without TLS, explicitly set `use_encryption: false`; otherwise HTTPS and certificate verification are enabled. The adapter builds `hardcharger://host:port` URIs, adding `?tls=false` only for plaintext.

For the standard `sqlmesh` command, import `sqlmesh_hardcharger` in a Python `config.py` before constructing your SQLMesh `Config`. For Python applications:

```python
import sqlmesh_hardcharger  # registers type: hardcharger
from sqlmesh import Context

context = Context(paths="path/to/project")
try:
    context.plan(auto_apply=True, no_prompts=True)
finally:
    context.close()
```

Use a separate PostgreSQL state connection for production, following [SQLMesh's state connection guidance](https://sqlmesh.readthedocs.io/en/stable/guides/configuration/#state-connection). The local DuckDB state connection above is for development. The tests also exercise state migrations on Hardcharger, but SQLMesh does not recommend this custom engine for production state storage.

## Features

- DuckDB SQL generation, SQLMesh plan/apply/run, incremental models, logical merges, SCD type 2 and table diffs.
- Arrow-native bulk DataFrame ingestion, including partial source columns, typed nulls and reordered columns.
- Native ADBC transactions and nested SQLMesh transaction scopes, with rollback on errors.
- Catalog discovery and switching, automatic schema creation, quoted identifiers and non-default catalogs.
- DuckLake with PostgreSQL metadata, partitioning and correct cascade behavior, inherited from current SQLMesh.
- Password, bearer token, browser OAuth/SSO, trusted external identity token and mutual TLS authentication through the native driver.

## Connection options

| Option | Default | Meaning |
| --- | --- | --- |
| `host` | `localhost` | Server hostname or IPv6 address |
| `port` | `31337` | Warp SQL port (1–65535) |
| `username`, `password` | unset | Password sign-in |
| `access_token` | unset | Hardcharger bearer token; omit password credentials |
| `subject_token` | unset | Trusted identity-provider token for token exchange; omit other credentials |
| `auth_type` | unset (password) | `password`, `external`, `client_certificate` or `mtls` |
| `use_encryption` | `true` | HTTPS; false explicitly opts into plain HTTP |
| `disable_certificate_verification` | `false` | Development-only TLS verification bypass |
| `tls_root_certs` | unset | PEM CA text or file path |
| `tls_client_cert`, `tls_client_key` | unset | PEM text or paths for mTLS |
| `tls_server_name` | unset | Certificate hostname / SNI override |
| `database` | unset | Existing catalog to select on each new connection |
| `concurrent_tasks` | `4` | Concurrent SQLMesh tasks |
| `register_comments` | `true` | Register model comments |
| `pre_ping` | `false` | Check pooled connections before use |

For browser sign-in, set `auth_type: external` and omit username/password/token. For client-certificate sign-in, set `auth_type: client_certificate`, provide the certificate and key, and omit password/token credentials. See the [driver authentication documentation](https://github.com/gizmodata/hardcharger-adbc/tree/main/python).

Catalog creation attaches a DuckDB file on the **server**. Dropping a catalog detaches it; it never deletes a file on the client or deletes the server's database file. Manage server files through your server administration process. Materialized views, managed models, SQLMesh grant synchronization and custom `when_matched` logical merge clauses are not advertised by this adapter.

## Development and testing

```bash
uv sync --extra dev --frozen
uv run ruff check .
uv run mypy sqlmesh_hardcharger
uv run pytest  # unit tests

# All inherited and Hardcharger-specific integration tests, including DuckLake:
docker compose -p sqlmesh-hardcharger -f tests/integration/docker/compose.hardcharger.yaml up -d --wait
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55441 uv run pytest -m integration

# Current upstream DuckDB and shared engine tests, over a real Hardcharger server:
uv run python scripts/test-upstream.py
```

The `hardcharger` development dependency downloads and verifies the released server binary on first use. Override it with `HARDCHARGER_SERVER_BINARY` when testing another build. A server is required for integration tests: they fail instead of silently skipping if it cannot start.

All 55 tests from [sqlmesh-gizmosql](https://github.com/gizmodata/sqlmesh-gizmosql/tree/0f4c37e91677b10e0a053cabea812de2ab31403a) are retained. The upstream runner pins SQLMesh v0.236.4 at `f6527ffbd8d54d91e26fab7d36c8f4a061bc6451`, uses the installed SQLMesh package, and replaces connection fixtures without changing assertions. Only the two MotherDuck-specific unit tests are deselected; the upstream suite's own unsupported-feature skips remain visible. Bump the pin and dependency range together when adopting a new SQLMesh API series.

CI tests Python 3.11–3.14, runs the upstream compatibility job, checks types and lint, builds the wheel/sdist, and publishes from version tags using PyPI Trusted Publishing with attestations. See [release setup](docs/releasing.md).

## License and origin

Apache-2.0. Adapted from GizmoData's SQLMesh GizmoSQL adapter, preserving its Git history and tests. DuckDB engine semantics are inherited from Apache-2.0 SQLMesh. Hardcharger and GizmoData are trademarks of GizmoData.
