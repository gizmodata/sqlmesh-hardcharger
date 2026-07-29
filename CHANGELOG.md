# Changelog

All notable changes to sqlmesh-gizmosql will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-07-29

### Changed

- Bumped `adbc-driver-gizmosql` minimum version to `>=2.0.0`. The 2.0
  driver is powered by the new
  [native Go GizmoSQL ADBC driver](https://github.com/gizmodata/gizmosql-adbc)
  — same API as 1.x, with DDL/DML immediate execution, `RETURNING`
  support, `gizmosql://` URIs, and OAuth/SSO provided by the shared Go
  driver library used across all languages.
- Raised all other dependency floors to current stable releases:
  `sqlmesh>=0.236.1`; dev extras `pytest>=9.1.1`, `pytest-cov>=7.1.0`,
  `mypy>=2.3.0`, `ruff>=0.16.0`, `gizmosql>=1.35.1`. Refreshed
  `uv.lock` accordingly.
- Bumped GitHub Actions to current majors in `ci.yml`:
  `actions/checkout@v7`, `actions/setup-python@v7`, `actions/cache@v6`,
  `actions/upload-artifact@v7`, `actions/download-artifact@v8`,
  `softprops/action-gh-release@v3`.

### Fixed

- DataFrame bulk ingestion works again with current dependencies: with
  driver 1.x and `arrow-adbc` 1.12, statement reuse after `adbc_ingest`
  was broken, failing the DataFrame bulk-ingestion path. Driver 2.0
  handles statement reuse in-driver, fixing ingestion in this
  dependency set.

## [0.2.5] - 2026-05-10

### Changed

- Surface the matching `## [X.Y.Z]` section from `CHANGELOG.md` as the
  GitHub Release body, mirroring the convention used in the upstream
  [GizmoSQL](https://github.com/gizmodata/gizmosql) repo. The CI release
  job now extracts release notes via `awk` and feeds them to
  `softprops/action-gh-release@v2` via `body_path`. If the matching
  section isn't found, the release is still created (with auto-generated
  notes) and a CI warning is logged.

## [0.2.4] - 2026-05-10

### Changed

- Switched the integration-test fixture from an externally-managed
  GizmoSQL Docker container to the
  [`gizmosql`](https://pypi.org/project/gizmosql/) PyPI package's
  managed subprocess. The duplicate `gizmosql_config` /
  `gizmosql_adapter` fixtures from each test module are consolidated
  into `tests/integration/conftest.py`; the docker-compose / CI
  services / Makefile targets / `wait-for-gizmosql.sh` script for the
  GizmoSQL container are removed. PostgreSQL is still spun up via
  docker-compose / CI services for the DuckLake tests.
- Bumped `sqlmesh` minimum version to `>=0.234.0`.
- Bumped `adbc-driver-gizmosql` minimum version to `>=1.1.6`.
- Added `gizmosql` to dev extras as the new test-fixture driver.

## [0.2.3] - 2026-04-11

### Changed

- Swapped the PyPI download-count badge to a `pepy.tech`-backed
  endpoint.

## [0.2.2] - 2026-04-11

### Changed

- Bumped `sqlmesh` minimum version from `>=0.100.0` to `>=0.232.0`.
- Removed the post-DDL/DML `fetchall()` workaround now that the ADBC
  driver handles execution itself (#5).

## [0.2.1] - 2026-04-11

### Changed

- Bumped `adbc-driver-gizmosql` minimum version from `>=1.1.3` to
  `>=1.1.5` (#3).

## [0.2.0] - 2026-03-30

### Changed

- Migrated from a Flight-SQL-direct client to
  `adbc-driver-gizmosql`'s `dbapi.connect()`.
- Added `auth_type="external"` for OAuth/SSO authentication.
- Fixed schema auto-creation for tables / CTAS in non-default
  catalogs.
- Added DuckLake integration tests covering multi-catalog scenarios
  (DuckDB ATTACH and DuckLake-on-PostgreSQL).
