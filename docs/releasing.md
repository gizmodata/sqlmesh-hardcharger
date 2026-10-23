# Publishing sqlmesh-hardcharger

## One-time PyPI setup

At https://pypi.org/manage/account/publishing/ add a **pending GitHub publisher**:

| Field | Exact value |
| --- | --- |
| PyPI project name | `sqlmesh-hardcharger` |
| GitHub owner | `gizmodata` |
| Repository name | `sqlmesh-hardcharger` |
| Workflow filename | `ci.yml` |
| Environment name | `release` |

Enter only the workflow filename, not `.github/workflows/ci.yml`. The GitHub `release` environment exists and accepts `v*` tags. No API token secret is needed. A pending publisher creates the PyPI project on the first successful upload; it does not reserve the name beforehand. After the first publication, manage it at https://pypi.org/manage/project/sqlmesh-hardcharger/settings/publishing/.

References: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/ and https://docs.pypi.org/trusted-publishers/adding-a-publisher/.

## Release

1. Update both package versions (`pyproject.toml` and `sqlmesh_hardcharger/__init__.py`), CHANGELOG and `uv.lock`.
2. Run CI on `main`, including the complete inherited/regression suite and pinned upstream tests.
3. Confirm the trusted publisher above is configured.
4. Tag the validated commit (`v1.0.0` for the first release) and push the tag.
5. The `ci.yml` workflow reruns tests, builds/checks artifacts, publishes with an OIDC identity and PyPI attestations, then creates the GitHub release.
6. Verify a fresh PyPI installation and published metadata/provenance. Update the Hardcharger integrations page only after PyPI publication succeeds.

A failed upload can be retried by rerunning the failed job; do not change the tag or attempt to overwrite a published version. Use a new version for changed artifacts.
