# Changelog

## [1.1.1] - 2026-11-05

### Fixed

- Require `adbc-driver-hardcharger` 2.3.0. A connection to a GizmoData Cloud cluster that is
  starting again (the server answers `server_resuming`) now waits for it, retrying after each
  `Retry-After` for up to 600 seconds, instead of failing at once. The driver also re-applies
  its session settings and session/query tags when the server replaces a lost session (idle
  eviction, an expired token, idle in a transaction); sqlmesh-hardcharger sets none of those
  itself, so this matters only for settings applied through the driver.

### Changed

- The tests run against Hardcharger 2.7.0 (`hardcharger>=2.7.0` in the `dev` extra), and
  `uv.lock` pins both.

## [1.1.0] - 2026-10-29

### Changed

- sqlmesh-hardcharger now uses the Chargewire protocol and drivers, the new name of the protocol the
  Hardcharger ADBC driver speaks. Nothing changes in connection configs, and it still works with
  Hardcharger servers released before the rename.
- Require `adbc-driver-hardcharger` 2.1.0, the first driver release that speaks Chargewire. The
  tests run against Hardcharger 2.3.0 (`hardcharger>=2.3.0` in the `dev` extra), and `uv.lock`
  pins both.

## [1.0.1] - 2026-10-23

- Point the README’s SQLMesh link to the verified official documentation, including the published PyPI description.

## [1.0.0] - 2026-10-23

- Initial Hardcharger release, ported from sqlmesh-gizmosql 0.3.1 with all 55 inherited tests.
- Native Hardcharger ADBC 2.0.2 over Chargewire HTTP(S), TLS by default, Python 3.11+.
- SQLMesh 0.236.4, the latest compatible transitive dependencies, refreshed development/build tools and lockfile.
- Reuse SQLMesh's current DuckDB implementation, including DuckLake partitioning and case-insensitive cascade detection.
- Fix partial source-column ingestion, typed missing values, native transaction handling, metadata discovery and quoted schema names.
- Add token/mTLS/custom CA options, per-connection default catalogs, IPv6 and a YAML-aware SQLMesh CLI.
- Add regression coverage and current upstream DuckDB/shared engine tests against real Hardcharger.
- Tag-gated PyPI Trusted Publishing with provenance attestations and GitHub release artifacts.

Earlier GizmoSQL releases remain in the preserved Git history and original repository.
