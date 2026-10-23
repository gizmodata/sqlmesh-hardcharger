# Changelog

## [1.0.0] - 2026-10-23

- Initial Hardcharger release, ported from sqlmesh-gizmosql 0.3.1 with all 55 inherited tests.
- Native Hardcharger ADBC 2.0.2 over Warp SQL HTTP(S), TLS by default, Python 3.11+.
- SQLMesh 0.236.4, the latest compatible transitive dependencies, refreshed development/build tools and lockfile.
- Reuse SQLMesh's current DuckDB implementation, including DuckLake partitioning and case-insensitive cascade detection.
- Fix partial source-column ingestion, typed missing values, native transaction handling, metadata discovery and quoted schema names.
- Add token/mTLS/custom CA options, per-connection default catalogs, IPv6 and a YAML-aware SQLMesh CLI.
- Add regression coverage and current upstream DuckDB/shared engine tests against real Hardcharger.
- Tag-gated PyPI Trusted Publishing with provenance attestations and GitHub release artifacts.

Earlier GizmoSQL releases remain in the preserved Git history and original repository.
