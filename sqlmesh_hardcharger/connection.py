"""
Hardcharger Connection Configuration for SQLMesh.

Provides the connection configuration class for Hardcharger servers.
"""

from __future__ import annotations

import atexit
import typing as t
import weakref

from pydantic import Field
from sqlmesh.core.config.common import concurrent_tasks_validator
from sqlmesh.core.config.connection import ConnectionConfig
from sqlmesh.core.engine_adapter import EngineAdapter
from sqlmesh.utils.errors import ConfigError
from sqlmesh.utils.pydantic import model_validator

from sqlmesh_hardcharger.adapter import HardchargerEngineAdapter

# Every connection the factory opened that may still be open. A process that exits without
# closing them (the CLI's fetchdf, a script) leaves the cleanup to garbage collection at
# shutdown, where a cursor can be collected before its connection: adbc-driver-manager then
# finds a statement it can no longer close and prints "Cannot close AdbcConnection with open
# AdbcStatement". Closing them at exit, while their cursors are still alive, closes each
# cursor first.
_open_connections: "weakref.WeakSet[t.Any]" = weakref.WeakSet()


@atexit.register
def _close_open_connections() -> None:
    for conn in list(_open_connections):
        try:
            conn.close()
        except Exception:  # noqa: BLE001 - a failed close must not hide the process's own exit
            pass


def _hardcharger_import_validator(cls: t.Any, data: t.Any) -> t.Any:
    """Validate that ADBC Hardcharger driver is installed."""
    check_import = data.pop("check_import", True) if isinstance(data, dict) else True
    if not check_import:
        return data
    try:
        import adbc_driver_hardcharger  # noqa: F401
    except ImportError:
        raise ConfigError(
            "Failed to import the 'adbc_driver_hardcharger' library. "
            "Please install it with: pip install sqlmesh-hardcharger "
            "or pip install adbc-driver-hardcharger"
        )
    return data


class HardchargerConnectionConfig(ConnectionConfig):
    """
    Hardcharger connection configuration.

    Hardcharger is a database server that uses DuckDB as its execution engine and
    exposes Chargewire over HTTP(S) for remote connections. This configuration
    uses the native Hardcharger ADBC driver.

    Args:
        host: The hostname of the Hardcharger server.
        port: The port of the Hardcharger server (default: 31337).
        username: The username for authentication (not needed with auth_type="external").
        password: The password for authentication (not needed with auth_type="external").
        use_encryption: Whether to use TLS encryption (default: True).
        disable_certificate_verification: Whether to skip TLS certificate verification.
            Useful for self-signed certificates in development (default: False).
        auth_type: Authentication type (e.g., "external" for browser-based OAuth/SSO).
        database: The default database/catalog to use.
        concurrent_tasks: The maximum number of concurrent tasks.
        register_comments: Whether to register model comments.
        pre_ping: Whether to pre-ping the connection.
    """

    host: str = "localhost"
    port: int = Field(default=31337, ge=1, le=65535)
    username: t.Optional[str] = None
    password: t.Optional[str] = None
    use_encryption: bool = True
    disable_certificate_verification: bool = False
    auth_type: t.Optional[t.Literal["password", "external", "client_certificate", "mtls"]] = None
    access_token: t.Optional[str] = None
    subject_token: t.Optional[str] = None
    tls_root_certs: t.Optional[str] = None
    tls_client_cert: t.Optional[str] = None
    tls_client_key: t.Optional[str] = None
    tls_server_name: t.Optional[str] = None
    database: t.Optional[str] = None

    concurrent_tasks: int = 4
    register_comments: bool = True
    pre_ping: bool = False

    type_: t.Literal["hardcharger"] = Field(alias="type", default="hardcharger")
    DIALECT: t.ClassVar[t.Literal["duckdb"]] = "duckdb"
    DISPLAY_NAME: t.ClassVar[t.Literal["Hardcharger"]] = "Hardcharger"
    DISPLAY_ORDER: t.ClassVar[t.Literal[17]] = 17

    _engine_import_validator = model_validator(mode="before")(_hardcharger_import_validator)
    _concurrent_tasks_validator = concurrent_tasks_validator

    @property
    def _connection_kwargs_keys(self) -> t.Set[str]:
        # ADBC uses a different connection pattern, so we don't pass these directly
        return set()

    @property
    def _engine_adapter(self) -> t.Type[EngineAdapter]:
        return HardchargerEngineAdapter

    @property
    def _connection_factory(self) -> t.Callable:
        """
        Create a connection factory for Hardcharger using adbc-driver-hardcharger.

        The connection is established using Chargewire over HTTP(S).
        """
        import re

        from adbc_driver_hardcharger import dbapi as hardcharger

        def connect() -> t.Any:
            # hardcharger:// is HTTPS by default; plaintext is an explicit opt-out.
            protocol = "hardcharger"
            host = (
                f"[{self.host}]"
                if ":" in self.host and not self.host.startswith("[")
                else self.host
            )
            uri = f"{protocol}://{host}:{self.port}"
            if not self.use_encryption:
                uri += "?tls=false"

            connect_kwargs: t.Dict[str, t.Any] = {"uri": uri, "autocommit": False}
            if self.auth_type:
                connect_kwargs["auth_type"] = self.auth_type
            if self.username:
                connect_kwargs["username"] = self.username
                connect_kwargs["password"] = self.password or ""
            if self.use_encryption and self.disable_certificate_verification:
                connect_kwargs["tls_skip_verify"] = True
            for key in (
                "access_token",
                "subject_token",
                "tls_root_certs",
                "tls_client_cert",
                "tls_client_key",
                "tls_server_name",
            ):
                if (value := getattr(self, key)) is not None:
                    connect_kwargs[key] = value
            if self.database:
                connect_kwargs["catalog"] = self.database

            conn = hardcharger.connect(**connect_kwargs)

            # Verify the backend is DuckDB - this adapter only supports the DuckDB backend
            try:
                vendor_version = conn.adbc_get_info().get("vendor_version", "")
            except BaseException:
                conn.close()
                raise
            if not re.search(
                pattern=r"\bduckdb\s+v?\d", string=vendor_version, flags=re.IGNORECASE
            ):
                conn.close()
                raise ConfigError(
                    f"Unsupported Hardcharger server backend: '{vendor_version}'. "
                    "This adapter only supports the DuckDB backend for Hardcharger."
                )

            _open_connections.add(conn)
            return conn

        return connect

    def get_catalog(self) -> t.Optional[str]:
        return self.database
