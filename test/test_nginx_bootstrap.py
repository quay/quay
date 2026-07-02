from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nginx_maps_original_remote_addr_for_quay_header():
    http_base = (ROOT / "conf/nginx/http-base.conf.jnj").read_text()

    assert "map $realip_remote_addr $quay_original_remote_addr" in http_base
    assert '""      $remote_addr;' in http_base
    assert "default $realip_remote_addr;" in http_base


def test_nginx_forwards_original_remote_addr_to_web_app():
    server_base = (ROOT / "conf/nginx/server-base.conf.jnj").read_text()

    assert "proxy_set_header X-Quay-Original-Remote-Addr $quay_original_remote_addr;" in server_base


def test_nginx_defines_bootstrap_renew_rate_limit_bucket():
    rate_limiting = (ROOT / "conf/nginx/rate-limiting.conf.jnj").read_text()

    assert "map $quay_original_remote_addr $bootstrap_renew_bucket" in rate_limiting
    assert '""      $binary_remote_addr;' in rate_limiting
    assert (
        "limit_req_zone $bootstrap_renew_bucket zone=bootstrap_renew:10m rate=10r/m;"
        in rate_limiting
    )


def test_nginx_rate_limits_bootstrap_renew_endpoint():
    server_base = (ROOT / "conf/nginx/server-base.conf.jnj").read_text()

    assert "location = /api/v1/bootstrap/renew" in server_base
    assert "limit_req zone=bootstrap_renew burst=5 nodelay;" in server_base
    assert server_base.index("location = /api/v1/bootstrap/renew") < server_base.index(
        "location /api/"
    )
