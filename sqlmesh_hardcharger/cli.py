"""SQLMesh CLI with the Hardcharger adapter registered before config loading."""


def main() -> None:
    from sqlmesh.cli.main import cli

    from sqlmesh_hardcharger import register

    register()
    cli()
