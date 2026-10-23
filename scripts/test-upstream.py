"""Run current SQLMesh engine tests over real Hardcharger connections.

Test assertions are upstream's. Only connection fixtures and the configured
gateway are replaced. MotherDuck-only tests are outside this adapter's scope.
"""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

VERSION = "0.236.4"
COMMIT = "f6527ffbd8d54d91e26fab7d36c8f4a061bc6451"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Existing pristine upstream checkout")
    args, pytest_args = parser.parse_known_args()
    with tempfile.TemporaryDirectory(prefix="hardcharger-sqlmesh-upstream-") as raw:
        root = Path(raw) / "sqlmesh"
        if args.source:
            actual = subprocess.check_output(
                ["git", "-C", str(args.source), "rev-parse", "HEAD"], text=True
            ).strip()
            if actual != COMMIT:
                raise RuntimeError(f"Expected upstream {COMMIT}, got {actual}")
            shutil.copytree(
                args.source,
                root,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )
        else:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    f"v{VERSION}",
                    "https://github.com/SQLMesh/sqlmesh.git",
                    str(root),
                ],
                check=True,
            )
            actual = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip()
            if actual != COMMIT:
                raise RuntimeError(f"Upstream tag moved: expected {COMMIT}, got {actual}")

        # Test the installed SQLMesh dependency, rather than importing its source
        # from this checkout. Keep examples and test helpers available upstream.
        (root / "sqlmesh").rename(root / "sqlmesh-source")
        # Upstream's sushi project loads these example entry points. Expose the
        # exact upstream package and metadata in this temporary test environment.
        custom = root / "examples/custom_materializations"
        shutil.copytree(custom / "custom_materializations", root / "custom_materializations")
        project = tomllib.loads((custom / "pyproject.toml").read_text())["project"]
        info = root / f"{project['name']}-{project['version']}.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {project['name']}\nVersion: {project['version']}\n"
        )
        entries = configparser.ConfigParser()
        entries.read_dict(project["entry-points"])
        with (info / "entry_points.txt").open("w") as f:
            entries.write(f)
        fixtures = Path(__file__).with_name("upstream_fixtures.py")
        shutil.copyfile(fixtures, root / "hardcharger_upstream_fixtures.py")
        engine_dir = root / "tests/core/engine_adapter"
        (engine_dir / "conftest.py").write_text(
            "from hardcharger_upstream_fixtures import *  # noqa: F403\n"
        )
        integration = engine_dir / "integration"
        with (integration / "conftest.py").open("a") as f:
            f.write("\nfrom hardcharger_upstream_fixtures import create_engine_adapter\n")

        import hardcharger

        with hardcharger.Server(
            extra_args=[
                "--init-sql-commands",
                f"SET secret_directory='{raw}/secrets'; ATTACH ':memory:' AS testing",
            ]
        ) as server:
            # The same gateway is used by upstream's SQLMesh plan/apply tests.
            (integration / "config.yaml").write_text(
                "gateways:\n  inttest_duckdb:\n    connection:\n      type: hardcharger\n"
                f"      host: {server.host}\n      port: {server.port}\n"
                f"      username: {server.username}\n      password: {server.password}\n"
                "      use_encryption: false\n      database: memory\n"
                "model_defaults:\n  dialect: duckdb\n"
            )
            env = dict(os.environ)
            env.update(
                {
                    "HARDCHARGER_UPSTREAM_HOST": server.host,
                    "HARDCHARGER_UPSTREAM_PORT": str(server.port),
                    "HARDCHARGER_UPSTREAM_USERNAME": server.username,
                    "HARDCHARGER_UPSTREAM_PASSWORD": server.password,
                    "PYTHONPATH": str(root),
                }
            )
            command = [
                sys.executable,
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "-m",
                "duckdb",
                "tests/core/engine_adapter/test_duckdb.py",
                "tests/core/engine_adapter/integration/test_integration.py",
                "--deselect=tests/core/engine_adapter/test_duckdb.py::test_create_catalog_motherduck",
                "--deselect=tests/core/engine_adapter/test_duckdb.py::test_drop_catalog_motherduck",
                "-ra",
                "--tb=short",
                *pytest_args,
            ]
            return subprocess.run(command, cwd=root, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
