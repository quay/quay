from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nginx_maps_bootstrap_renewal_location_from_original_remote_addr():
    http_base = (ROOT / "conf/nginx/http-base.conf.jnj").read_text()

    assert "map $realip_remote_addr $quay_original_remote_addr" in http_base
    assert '""      $remote_addr;' in http_base
    assert "default $realip_remote_addr;" in http_base
    assert "map $quay_original_remote_addr $quay_bootstrap_renewal_location" in http_base
    assert "default remote;" in http_base
    assert "127.0.0.1 local;" in http_base
    assert "::1 local;" in http_base
    assert r"~*^::ffff:127\.0\.0\.1$ local;" in http_base


def test_nginx_passes_bootstrap_renewal_location_only_to_renew_endpoint():
    server_base = (ROOT / "conf/nginx/server-base.conf.jnj").read_text()

    assert "location = /api/v1/bootstrap/renew" in server_base
    assert server_base.index("location = /api/v1/bootstrap/renew") < server_base.index(
        "location /api/"
    )
    assert server_base.count("proxy_set_header X-Quay-Bootstrap-Renewal-Location") == 1
    assert (
        "proxy_set_header X-Quay-Bootstrap-Renewal-Location " "$quay_bootstrap_renewal_location;"
    ) in server_base

    common_proxy_block = server_base.split("location /angular", 1)[0]
    assert "X-Quay-Bootstrap-Renewal-Location" not in common_proxy_block


def test_nginx_renew_location_repeats_common_proxy_headers():
    server_base = (ROOT / "conf/nginx/server-base.conf.jnj").read_text()
    renew_block = server_base.split("location = /api/v1/bootstrap/renew", 1)[1].split(
        "location /api/", 1
    )[0]

    assert "proxy_set_header X-Forwarded-For $proper_forwarded_for;" in renew_block
    assert "proxy_set_header X-Forwarded-Proto $final_proto;" in renew_block
    assert "proxy_set_header Transfer-Encoding $http_transfer_encoding;" in renew_block
    assert "proxy_set_header Host $safe_host;" in renew_block
    assert "proxy_set_header X-Forwarded-Host $safe_host;" in renew_block
    assert "limit_req zone=dynamicauth_heavy_http1 burst=25 nodelay;" in renew_block
    assert "limit_req zone=dynamicauth_heavy_http2 burst=100 nodelay;" in renew_block
