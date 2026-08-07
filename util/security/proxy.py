"""Connection-time pinning for validated mirror proxy destinations."""

import logging
import socket
import socketserver
import ssl
import threading
from contextlib import ExitStack, contextmanager
from typing import Dict, Iterator, List, Mapping, Optional, Set

from util.security.ssrf import ValidatedMirrorProxy, validate_mirror_proxy_config

logger = logging.getLogger(__name__)

MIRROR_PROXY_VALIDATION_ERROR = "Mirror proxy location is not allowed"


class MirrorProxyValidationError(ValueError):
    """Raised when mirror proxy validation fails at a connection boundary."""

    def __init__(self):
        super().__init__(MIRROR_PROXY_VALIDATION_ERROR)


_CONNECT_TIMEOUT = 30


class _PinnedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, proxy: ValidatedMirrorProxy):
        self.proxy = proxy
        self._connections: Set[socket.socket] = set()
        self._connections_lock = threading.Lock()
        self._closing = False
        super().__init__(("127.0.0.1", 0), _PinnedProxyHandler)

    def track_connections(self, *connections) -> bool:
        with self._connections_lock:
            if self._closing:
                for connection in connections:
                    connection.close()
                return False
            self._connections.update(connections)
            return True

    def untrack_connections(self, *connections):
        with self._connections_lock:
            self._connections.difference_update(connections)

    def close_connections(self):
        with self._connections_lock:
            self._closing = True
            connections = list(self._connections)
            self._connections.clear()

        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    def open_remote(self):
        last_error = None
        for ip in self.proxy.resolved_ips:
            try:
                remote = socket.create_connection(
                    (ip, self.proxy.port),
                    timeout=_CONNECT_TIMEOUT,
                )
                if self.proxy.scheme == "https":
                    context = ssl.create_default_context()
                    remote = context.wrap_socket(remote, server_hostname=self.proxy.hostname)
                remote.settimeout(None)
                return remote
            except OSError as e:
                last_error = e

        if last_error is not None:
            raise last_error
        raise OSError("Proxy destination has no validated addresses")


class _PinnedProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            remote = self.server.open_remote()
        except OSError:
            logger.warning("Unable to connect to a validated mirror proxy destination")
            return

        if not self.server.track_connections(self.request, remote):
            return

        try:
            forward = threading.Thread(
                target=self._copy,
                args=(self.request, remote),
                daemon=True,
            )
            forward.start()
            self._copy(remote, self.request)
            forward.join(timeout=1)
        finally:
            self.server.untrack_connections(self.request, remote)
            remote.close()

    @staticmethod
    def _copy(source, destination):
        try:
            while True:
                data = source.recv(64 * 1024)
                if not data:
                    break
                destination.sendall(data)
        except OSError:
            pass
        finally:
            try:
                destination.shutdown(socket.SHUT_WR)
            except OSError:
                pass


class _PinnedProxyRelay:
    def __init__(self, proxy: ValidatedMirrorProxy):
        self._proxy = proxy
        self._server = _PinnedProxyServer(proxy)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )

    @property
    def url(self) -> str:
        userinfo = f"{self._proxy.userinfo}@" if self._proxy.userinfo else ""
        port = self._server.server_address[1]
        return f"http://{userinfo}127.0.0.1:{port}"

    def start(self):
        self._thread.start()

    def close(self):
        self._server.shutdown()
        self._server.close_connections()
        self._server.server_close()
        self._thread.join(timeout=1)


@contextmanager
def pinned_mirror_proxy_config(
    proxy_config: Optional[Mapping[str, object]],
    allowed_hosts: Optional[List[str]] = None,
) -> Iterator[Dict[str, object]]:
    """Yield proxy settings routed through the exact addresses validated here.

    A short-lived loopback relay prevents Requests or Skopeo from resolving the
    user-controlled proxy hostname a second time. For HTTPS proxies, the relay
    establishes TLS using the original hostname for certificate verification.
    """
    try:
        validated = validate_mirror_proxy_config(
            proxy_config,
            resolve_dns=True,
            allowed_hosts=allowed_hosts,
        )
    except ValueError:
        raise MirrorProxyValidationError() from None
    pinned: Dict[str, object] = {}
    if proxy_config:
        no_proxy = proxy_config.get("no_proxy")
        if no_proxy is not None:
            pinned["no_proxy"] = no_proxy

    with ExitStack() as stack:
        for key, proxy in validated.items():
            relay = _PinnedProxyRelay(proxy)
            relay.start()
            stack.callback(relay.close)
            pinned[key] = relay.url
        yield pinned
