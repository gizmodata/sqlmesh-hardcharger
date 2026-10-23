"""Unit tests for Hardcharger engine adapter and connection config.

These tests don't require a running Hardcharger server - they test
configuration validation and adapter properties.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlmesh.utils.errors import ConfigError

from sqlmesh_hardcharger.adapter import HardchargerEngineAdapter
from sqlmesh_hardcharger.connection import HardchargerConnectionConfig


class TestHardchargerConnectionConfig:
    """Tests for HardchargerConnectionConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HardchargerConnectionConfig(
            username="user",
            password="pass",
        )

        assert config.host == "localhost"
        assert config.port == 31337
        assert config.use_encryption is True
        assert config.disable_certificate_verification is False
        assert config.auth_type is None
        assert config.database is None
        assert config.concurrent_tasks == 4

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HardchargerConnectionConfig(
            host="hardcharger.example.com",
            port=12345,
            username="testuser",
            password="testpass",
            use_encryption=False,
            disable_certificate_verification=True,
            database="mydb",
            concurrent_tasks=8,
        )

        assert config.host == "hardcharger.example.com"
        assert config.port == 12345
        assert config.username == "testuser"
        assert config.password == "testpass"
        assert config.use_encryption is False
        assert config.disable_certificate_verification is True
        assert config.database == "mydb"
        assert config.concurrent_tasks == 8

    def test_external_auth_no_credentials(self):
        """Test that auth_type=external works without username/password."""
        config = HardchargerConnectionConfig(
            auth_type="external",
        )

        assert config.auth_type == "external"
        assert config.username is None
        assert config.password is None

    def test_dialect_is_duckdb(self):
        """Test that the dialect is set to duckdb."""
        config = HardchargerConnectionConfig(
            username="user",
            password="pass",
        )
        assert config.DIALECT == "duckdb"

    def test_type_is_hardcharger(self):
        """Test that the type is set to hardcharger."""
        config = HardchargerConnectionConfig(
            username="user",
            password="pass",
        )
        assert config.type_ == "hardcharger"

    def test_get_catalog(self):
        """Test get_catalog returns database."""
        config = HardchargerConnectionConfig(
            username="user",
            password="pass",
            database="mydb",
        )
        assert config.get_catalog() == "mydb"

    def test_get_catalog_none(self):
        """Test get_catalog returns None when database not set."""
        config = HardchargerConnectionConfig(
            username="user",
            password="pass",
        )
        assert config.get_catalog() is None

    def test_connection_factory_builds_correct_uri_with_tls(self):
        """Test connection factory builds correct URI with TLS."""
        mock_connect = MagicMock()
        mock_conn = MagicMock()
        mock_conn.adbc_get_info.return_value = {"vendor_version": "duckdb v1.0.0"}
        mock_connect.return_value = mock_conn

        config = HardchargerConnectionConfig(
            host="example.com",
            port=31337,
            username="user",
            password="pass",
            use_encryption=True,
            disable_certificate_verification=False,
        )

        mock_dbapi = MagicMock()
        mock_dbapi.connect = mock_connect
        mock_module = MagicMock()
        mock_module.dbapi = mock_dbapi

        with patch.dict(
            "sys.modules",
            {"adbc_driver_hardcharger": mock_module, "adbc_driver_hardcharger.dbapi": mock_dbapi},
        ):
            factory = config._connection_factory
            factory()

        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["uri"] == "hardcharger://example.com:31337"
        assert call_kwargs["username"] == "user"
        assert call_kwargs["password"] == "pass"
        assert "tls_skip_verify" not in call_kwargs

    def test_connection_factory_builds_correct_uri_without_tls(self):
        """Test connection factory builds correct URI without TLS."""
        mock_connect = MagicMock()
        mock_conn = MagicMock()
        mock_conn.adbc_get_info.return_value = {"vendor_version": "duckdb v1.0.0"}
        mock_connect.return_value = mock_conn

        config = HardchargerConnectionConfig(
            host="example.com",
            port=31337,
            username="user",
            password="pass",
            use_encryption=False,
        )

        mock_dbapi = MagicMock()
        mock_dbapi.connect = mock_connect
        mock_module = MagicMock()
        mock_module.dbapi = mock_dbapi

        with patch.dict(
            "sys.modules",
            {"adbc_driver_hardcharger": mock_module, "adbc_driver_hardcharger.dbapi": mock_dbapi},
        ):
            factory = config._connection_factory
            factory()

        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["uri"] == "hardcharger://example.com:31337?tls=false"

    def test_connection_factory_with_tls_skip_verify(self):
        """Test connection factory passes tls_skip_verify when configured."""
        mock_connect = MagicMock()
        mock_conn = MagicMock()
        mock_conn.adbc_get_info.return_value = {"vendor_version": "duckdb v1.0.0"}
        mock_connect.return_value = mock_conn

        config = HardchargerConnectionConfig(
            host="example.com",
            port=31337,
            username="user",
            password="pass",
            use_encryption=True,
            disable_certificate_verification=True,
        )

        mock_dbapi = MagicMock()
        mock_dbapi.connect = mock_connect
        mock_module = MagicMock()
        mock_module.dbapi = mock_dbapi

        with patch.dict(
            "sys.modules",
            {"adbc_driver_hardcharger": mock_module, "adbc_driver_hardcharger.dbapi": mock_dbapi},
        ):
            factory = config._connection_factory
            factory()

        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["tls_skip_verify"] is True

    def test_connection_factory_with_auth_type(self):
        """Test connection factory passes auth_type for OAuth/SSO."""
        mock_connect = MagicMock()
        mock_conn = MagicMock()
        mock_conn.adbc_get_info.return_value = {"vendor_version": "duckdb v1.0.0"}
        mock_connect.return_value = mock_conn

        config = HardchargerConnectionConfig(
            host="example.com",
            port=31337,
            auth_type="external",
        )

        mock_dbapi = MagicMock()
        mock_dbapi.connect = mock_connect
        mock_module = MagicMock()
        mock_module.dbapi = mock_dbapi

        with patch.dict(
            "sys.modules",
            {"adbc_driver_hardcharger": mock_module, "adbc_driver_hardcharger.dbapi": mock_dbapi},
        ):
            factory = config._connection_factory
            factory()

        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["auth_type"] == "external"
        assert "username" not in call_kwargs
        assert "password" not in call_kwargs

    def test_connection_factory_rejects_non_duckdb_backend(self):
        """Test connection factory raises error for non-DuckDB backend."""
        mock_connect = MagicMock()
        mock_conn = MagicMock()
        mock_conn.adbc_get_info.return_value = {"vendor_version": "sqlite v3.40.0"}
        mock_connect.return_value = mock_conn

        config = HardchargerConnectionConfig(
            host="example.com",
            port=31337,
            username="user",
            password="pass",
        )

        mock_dbapi = MagicMock()
        mock_dbapi.connect = mock_connect
        mock_module = MagicMock()
        mock_module.dbapi = mock_dbapi

        with patch.dict(
            "sys.modules",
            {"adbc_driver_hardcharger": mock_module, "adbc_driver_hardcharger.dbapi": mock_dbapi},
        ):
            factory = config._connection_factory
            with pytest.raises(ConfigError, match="Unsupported Hardcharger server backend"):
                factory()

        # Verify connection was closed after rejection
        mock_conn.close.assert_called_once()


class TestHardchargerEngineAdapter:
    """Tests for HardchargerEngineAdapter properties."""

    def test_dialect(self):
        """Test that dialect is duckdb."""
        assert HardchargerEngineAdapter.DIALECT == "duckdb"

    def test_supports_transactions(self):
        """Test transactions are supported via SQL statements."""
        assert HardchargerEngineAdapter.SUPPORTS_TRANSACTIONS is True

    def test_supports_create_drop_catalog(self):
        """Test catalog operations are supported."""
        assert HardchargerEngineAdapter.SUPPORTS_CREATE_DROP_CATALOG is True

    def test_supported_drop_cascade_object_kinds(self):
        """Test cascade drop is supported for schemas, tables, and views."""
        assert "SCHEMA" in HardchargerEngineAdapter.SUPPORTED_DROP_CASCADE_OBJECT_KINDS
        assert "TABLE" in HardchargerEngineAdapter.SUPPORTED_DROP_CASCADE_OBJECT_KINDS
        assert "VIEW" in HardchargerEngineAdapter.SUPPORTED_DROP_CASCADE_OBJECT_KINDS


class TestRegistration:
    """Tests for automatic registration with SQLMesh."""

    def test_adapter_registered(self):
        """Test that adapter is registered in SQLMesh's dialect map."""
        from sqlmesh.core import engine_adapter

        import sqlmesh_hardcharger  # noqa: F401

        assert "hardcharger" in engine_adapter.DIALECT_TO_ENGINE_ADAPTER
        assert engine_adapter.DIALECT_TO_ENGINE_ADAPTER["hardcharger"] is HardchargerEngineAdapter

    def test_connection_config_registered(self):
        """Test that connection config is registered in SQLMesh."""
        from sqlmesh.core.config import connection as conn_module

        import sqlmesh_hardcharger  # noqa: F401

        assert "hardcharger" in conn_module.CONNECTION_CONFIG_TO_TYPE
        assert conn_module.CONNECTION_CONFIG_TO_TYPE["hardcharger"] is HardchargerConnectionConfig

    def test_dialect_type_registered(self):
        """Test that dialect type is registered."""
        from sqlmesh.core.config import connection as conn_module

        import sqlmesh_hardcharger  # noqa: F401

        assert "hardcharger" in conn_module.DIALECT_TO_TYPE
        assert conn_module.DIALECT_TO_TYPE["hardcharger"] == "duckdb"
