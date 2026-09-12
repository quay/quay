from unittest.mock import Mock, patch

from util.security.proxy import _PinnedProxyServer
from util.security.ssrf import ValidatedMirrorProxy


def _proxy(scheme="http"):
    return ValidatedMirrorProxy(
        scheme=scheme,
        hostname="proxy.example.com",
        port=8443,
        userinfo=None,
        resolved_ips=("93.184.216.34", "93.184.216.35"),
    )


def test_relay_connects_to_validated_ip_instead_of_resolving_hostname():
    remote = Mock()
    server = _PinnedProxyServer(_proxy())
    try:
        with patch("util.security.proxy.socket.create_connection", return_value=remote) as connect:
            assert server.open_remote() is remote
    finally:
        server.server_close()

    connect.assert_called_once_with(("93.184.216.34", 8443), timeout=30)


def test_https_relay_preserves_original_hostname_for_tls_verification():
    remote = Mock()
    wrapped = Mock()
    context = Mock()
    context.wrap_socket.return_value = wrapped
    server = _PinnedProxyServer(_proxy("https"))
    try:
        with patch("util.security.proxy.socket.create_connection", return_value=remote):
            with patch("util.security.proxy.ssl.create_default_context", return_value=context):
                assert server.open_remote() is wrapped
    finally:
        server.server_close()

    context.wrap_socket.assert_called_once_with(remote, server_hostname="proxy.example.com")


def test_relay_shutdown_closes_active_tunnels_and_rejects_new_ones():
    client = Mock()
    remote = Mock()
    late_connection = Mock()
    server = _PinnedProxyServer(_proxy())
    try:
        assert server.track_connections(client, remote)

        server.close_connections()

        assert not server.track_connections(late_connection)
    finally:
        server.server_close()

    client.shutdown.assert_called_once()
    client.close.assert_called_once()
    remote.shutdown.assert_called_once()
    remote.close.assert_called_once()
    late_connection.close.assert_called_once()
