"""
SQLMesh Hardcharger Adapter.

This package provides Hardcharger support for SQLMesh. When imported, it automatically
registers the Hardcharger engine adapter and connection configuration with SQLMesh.

Usage:
    # Option 1: Explicit import (recommended for clarity)
    import sqlmesh_hardcharger
    from sqlmesh import Context

    # Option 2: Just import - registration happens automatically
    import sqlmesh_hardcharger  # noqa: F401

    # Then use SQLMesh normally with type: hardcharger in your config

Example config.yaml:
    gateways:
      my_hardcharger:
        connection:
          type: hardcharger
          host: localhost
          port: 31337
          username: user
          password: pass
          database: my_database
"""

from sqlmesh_hardcharger.adapter import HardchargerEngineAdapter
from sqlmesh_hardcharger.connection import HardchargerConnectionConfig

__version__ = "1.0.0"
__all__ = ["HardchargerEngineAdapter", "HardchargerConnectionConfig", "register", "__version__"]

_registered = False


def register() -> None:
    """
    Register Hardcharger adapter and connection config with SQLMesh.

    This function is called automatically when the module is imported,
    but can also be called explicitly if needed.
    """
    global _registered
    if _registered:
        return

    # Register the engine adapter
    from sqlmesh.core import engine_adapter

    if "hardcharger" not in engine_adapter.DIALECT_TO_ENGINE_ADAPTER:
        engine_adapter.DIALECT_TO_ENGINE_ADAPTER["hardcharger"] = HardchargerEngineAdapter

    # Register the connection config
    from sqlmesh.core.config import connection as conn_module

    if "hardcharger" not in conn_module.CONNECTION_CONFIG_TO_TYPE:
        conn_module.CONNECTION_CONFIG_TO_TYPE["hardcharger"] = HardchargerConnectionConfig

    if "hardcharger" not in conn_module.DIALECT_TO_TYPE:
        conn_module.DIALECT_TO_TYPE["hardcharger"] = HardchargerConnectionConfig.DIALECT

    _registered = True


# Auto-register on import
register()
