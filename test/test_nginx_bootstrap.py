import shutil
from pathlib import Path

from conf.init import nginx_conf_create

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


def test_nginx_renders_configured_ecdh_curves_for_all_tls_listeners(tmp_path, monkeypatch):
    nginx_dir = tmp_path / "nginx"
    stack_dir = tmp_path / "stack"
    nginx_dir.mkdir()
    stack_dir.mkdir()
    (stack_dir / "ssl.key").touch()
    shutil.copy(ROOT / "conf/nginx/nginx.conf.jnj", nginx_dir / "nginx.conf.jnj")

    monkeypatch.setattr(nginx_conf_create, "QUAYCONF_DIR", str(tmp_path))
    monkeypatch.setattr(nginx_conf_create, "STATIC_DIR", "/static")

    nginx_conf_create.generate_nginx_config(
        {"SSL_ECDH_CURVES": ["X25519MLKEM768", "X25519", "prime256v1"]}
    )

    rendered = (nginx_dir / "nginx.conf").read_text()
    assert "ssl_ecdh_curve X25519MLKEM768:X25519:prime256v1;" in rendered
    assert rendered.count("listen 8443 ssl") == 1
    assert rendered.count("listen 7443 ssl") == 1
    assert rendered.count("listen 55443 ssl") == 1


def test_nginx_omits_ecdh_curve_directive_when_unset(tmp_path, monkeypatch):
    nginx_dir = tmp_path / "nginx"
    stack_dir = tmp_path / "stack"
    nginx_dir.mkdir()
    stack_dir.mkdir()
    (stack_dir / "ssl.key").touch()
    shutil.copy(ROOT / "conf/nginx/nginx.conf.jnj", nginx_dir / "nginx.conf.jnj")

    monkeypatch.setattr(nginx_conf_create, "QUAYCONF_DIR", str(tmp_path))
    monkeypatch.setattr(nginx_conf_create, "STATIC_DIR", "/static")

    nginx_conf_create.generate_nginx_config({})

    rendered = (nginx_dir / "nginx.conf").read_text()
    assert "ssl_ecdh_curve" not in rendered
    assert rendered.count("listen 8443 ssl") == 1
    assert rendered.count("listen 7443 ssl") == 1
    assert rendered.count("listen 55443 ssl") == 1


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
