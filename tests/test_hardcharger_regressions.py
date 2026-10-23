"""Hardcharger transport and SQLMesh configuration regression coverage."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from sqlmesh_hardcharger import HardchargerConnectionConfig


@pytest.fixture
def connect():
    with patch("adbc_driver_hardcharger.dbapi.connect") as connect:
        connect.return_value.adbc_get_info.return_value = {
            "vendor_name": "Hardcharger",
            "vendor_version": "2.0.0 (DuckDB v2.0.0)",
        }
        yield connect


def test_real_server_metadata_and_native_transactions(connect):
    config = HardchargerConnectionConfig()
    assert config._connection_factory() is connect.return_value
    assert connect.call_args.kwargs["autocommit"] is False


def test_metadata_failure_releases_connection(connect):
    connect.return_value.adbc_get_info.side_effect = RuntimeError("metadata unavailable")
    with pytest.raises(RuntimeError, match="metadata unavailable"):
        HardchargerConnectionConfig()._connection_factory()
    connect.return_value.close.assert_called_once()


@pytest.mark.parametrize("host", ["::1", "[::1]"])
def test_ipv6_literal_is_bracketed_once(connect, host):
    HardchargerConnectionConfig(host=host)._connection_factory()
    assert connect.call_args.kwargs["uri"] == "hardcharger://[::1]:31337"


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_invalid_ports_rejected(port):
    with pytest.raises(ValidationError):
        HardchargerConnectionConfig(port=port)


def test_catalog_token_and_custom_ca_reach_driver(connect):
    HardchargerConnectionConfig(
        database="analytics",
        access_token="test-token",
        tls_root_certs="/test/ca.pem",
        tls_server_name="db.example.com",
    )._connection_factory()
    assert connect.call_args.kwargs["catalog"] == "analytics"
    assert connect.call_args.kwargs["access_token"] == "test-token"
    assert connect.call_args.kwargs["tls_root_certs"] == "/test/ca.pem"
    assert connect.call_args.kwargs["tls_server_name"] == "db.example.com"


def test_client_certificate_sign_in(connect):
    HardchargerConnectionConfig(
        auth_type="client_certificate",
        tls_client_cert="/test/client.pem",
        tls_client_key="/test/client-key.pem",
    )._connection_factory()
    assert connect.call_args.kwargs["auth_type"] == "client_certificate"
    assert connect.call_args.kwargs["tls_client_cert"] == "/test/client.pem"
    assert "username" not in connect.call_args.kwargs


def test_invalid_auth_mode_rejected():
    with pytest.raises(ValidationError):
        HardchargerConnectionConfig(auth_type="typo")


def test_cli_delegates_after_registration():
    from sqlmesh_hardcharger.cli import main

    cli = MagicMock()
    with patch("sqlmesh.cli.main.cli", cli):
        main()
    cli.assert_called_once_with()
