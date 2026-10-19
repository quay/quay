"""
System metrics collector — samples Unix socket queue depth and active
connections by reading ``/proc/net/unix`` and pushes to the pod-local
Pushgateway.

Runs as a standalone supervisord process, independent of Gunicorn workers
and gevent scheduling.  Failure of this collector never affects pod
readiness or request serving.

Queue depth is measured by counting pending (not-yet-accepted) connections
in ``/proc/net/unix``.  These appear as entries with state ``02`` (connected)
and inode ``0``.  Active connections (accepted by gunicorn) appear as
state ``03`` entries.

Sampling happens every SAMPLE_INTERVAL_SECONDS (default 5s).  Metrics are
pushed to the Pushgateway every PUSH_INTERVAL_SECONDS (default 30s).
A Prometheus histogram records queue depth distribution across samples,
enabling percentile queries and alerting on sustained saturation.
"""

import logging
import os
import socket
import time

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    push_to_gateway,
)

logger = logging.getLogger(__name__)

PUSHGATEWAY_URL = "localhost:9091"
PUSH_JOB = "system_metrics_collector"
SAMPLE_INTERVAL_SECONDS = max(1, int(os.getenv("SYSTEM_METRICS_SAMPLE_INTERVAL", "5")))
PUSH_INTERVAL_SECONDS = max(1, int(os.getenv("SYSTEM_METRICS_PUSH_INTERVAL", "30")))
PROC_NET_UNIX = "/proc/net/unix"
QUEUE_DEPTH_BUCKETS = (0, 10, 50, 100, 250, 500, 1000, 1500, 2000, 2048)

SOCKET_CONFIGS = [
    {"path": "/tmp/gunicorn_registry.sock", "name": "registry"},
    {"path": "/tmp/gunicorn_web.sock", "name": "web"},
    {"path": "/tmp/gunicorn_secscan.sock", "name": "secscan"},
]


def _build_registry():
    registry = CollectorRegistry()
    hostname = socket.gethostname()

    metrics = {
        "queue_depth": Gauge(
            "gunicorn_socket_queue_depth",
            "Connections currently waiting for Gunicorn to accept",
            labelnames=["host", "socket"],
            registry=registry,
        ),
        "queue_depth_hist": Histogram(
            "gunicorn_socket_queue_depth_samples",
            "Distribution of queue depth observations across sample intervals",
            labelnames=["host", "socket"],
            buckets=QUEUE_DEPTH_BUCKETS,
            registry=registry,
        ),
        "active_connections": Gauge(
            "gunicorn_socket_active_connections",
            "Connections accepted by Gunicorn and currently being served",
            labelnames=["host", "socket"],
            registry=registry,
        ),
        "socket_present": Gauge(
            "gunicorn_socket_present",
            "1 if the socket file exists, 0 otherwise",
            labelnames=["host", "socket"],
            registry=registry,
        ),
        "collector_errors": Counter(
            "system_metrics_collector_errors_total",
            "Errors encountered by the collector",
            labelnames=["host"],
            registry=registry,
        ),
        "last_sample_timestamp": Gauge(
            "system_metrics_collector_last_sample_timestamp_seconds",
            "Unix timestamp of the last successful sample",
            labelnames=["host"],
            registry=registry,
        ),
    }
    return registry, metrics, hostname


def _read_proc_net_unix(proc_path=PROC_NET_UNIX):
    """Read /proc/net/unix and return per-socket pending and active counts.

    Returns a dict of ``{socket_path: {"pending": int, "active": int}}``.

    Pending connections (state ``02``, inode ``0``) are in the listen queue
    waiting for gunicorn to ``accept()``.  Active connections (state ``03``)
    have been accepted and are being served.

    Each line in ``/proc/net/unix`` has the following format::

        Num       RefCount Protocol Flags    Type St Inode Path
        92d0f433: 00000002 00000000 00010000 0001 01 1158022 /tmp/gunicorn_registry.sock
        cd32b376: 00000002 00000000 00000000 0001 02       0 /tmp/gunicorn_registry.sock
        56665bdb: 00000002 00000000 00000000 0001 03 1167596 /tmp/gunicorn_registry.sock

    Fields: Num(0) RefCount(1) Protocol(2) Flags(3) Type(4) St(5) Inode(6) Path(7)
    """
    stats = {}
    try:
        with open(proc_path) as f:
            f.readline()  # skip header
            for line in f:
                fields = line.split()
                # Lines without a path (e.g. abstract or unnamed sockets)
                # have fewer than 8 fields — skip them.
                if len(fields) < 8:
                    continue
                state = fields[5]
                inode = fields[6]
                path = fields[7]
                if path not in stats:
                    stats[path] = {"pending": 0, "active": 0}
                if state == "02" and inode == "0":
                    stats[path]["pending"] += 1
                elif state == "03":
                    stats[path]["active"] += 1
    except OSError as exc:
        logger.warning("Failed to read %s: %s", proc_path, exc)
        raise
    return stats


def _sample(metrics, hostname):
    """Take one sample, update gauges, and record a histogram observation."""
    try:
        socket_stats = _read_proc_net_unix()
    except OSError:
        metrics["collector_errors"].labels(host=hostname).inc()
        return

    for sock_cfg in SOCKET_CONFIGS:
        sock_name = sock_cfg["name"]
        sock_path = sock_cfg["path"]

        present = os.path.exists(sock_path)
        metrics["socket_present"].labels(host=hostname, socket=sock_name).set(int(present))

        pending = socket_stats.get(sock_path, {}).get("pending", 0)
        active = socket_stats.get(sock_path, {}).get("active", 0)

        metrics["queue_depth"].labels(host=hostname, socket=sock_name).set(pending)
        metrics["queue_depth_hist"].labels(host=hostname, socket=sock_name).observe(pending)
        metrics["active_connections"].labels(host=hostname, socket=sock_name).set(active)

    metrics["last_sample_timestamp"].labels(host=hostname).set(time.time())


def _push(registry, metrics, hostname):
    """Push metrics to the Pushgateway."""
    try:
        push_to_gateway(
            PUSHGATEWAY_URL,
            job=PUSH_JOB,
            registry=registry,
            grouping_key={"host": hostname},
        )
        logger.debug("Pushed socket metrics to pushgateway")
    except Exception:
        logger.warning("Failed to push to pushgateway", exc_info=True)
        metrics["collector_errors"].labels(host=hostname).inc()


def main():
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("DEBUGLOG", "false").lower() == "true" else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info(
        "Starting system metrics collector "
        "(sample_interval=%ds, push_interval=%ds, pushgateway=%s)",
        SAMPLE_INTERVAL_SECONDS,
        PUSH_INTERVAL_SECONDS,
        PUSHGATEWAY_URL,
    )

    registry, metrics, hostname = _build_registry()
    last_push = time.monotonic()

    while True:
        _sample(metrics, hostname)

        elapsed = time.monotonic() - last_push
        if elapsed >= PUSH_INTERVAL_SECONDS:
            _push(registry, metrics, hostname)
            last_push = time.monotonic()

        time.sleep(SAMPLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
