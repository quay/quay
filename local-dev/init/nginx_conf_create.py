import os
import os.path

import yaml
import jinja2

QUAYPATH = os.getenv("QUAYPATH", ".")
QUAYDIR = os.getenv("QUAYDIR", "/")
QUAYCONF_DIR = os.getenv("QUAYCONF", os.path.join(QUAYDIR, QUAYPATH, "conf"))
STATIC_DIR = os.path.join(QUAYDIR, "static")

SSL_PROTOCOL_DEFAULTS = ["TLSv1", "TLSv1.1", "TLSv1.2"]
SSL_CIPHER_DEFAULTS = [
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "DHE-RSA-AES128-GCM-SHA256",
    "DHE-DSS-AES128-GCM-SHA256",
    "kEDH+AESGCM",
    "ECDHE-RSA-AES128-SHA256",
    "ECDHE-ECDSA-AES128-SHA256",
    "ECDHE-RSA-AES128-SHA",
    "ECDHE-ECDSA-AES128-SHA",
    "ECDHE-RSA-AES256-SHA384",
    "ECDHE-ECDSA-AES256-SHA384",
    "ECDHE-RSA-AES256-SHA",
    "ECDHE-ECDSA-AES256-SHA",
    "DHE-RSA-AES128-SHA256",
    "DHE-RSA-AES128-SHA",
    "DHE-DSS-AES128-SHA256",
    "DHE-RSA-AES256-SHA256",
    "DHE-DSS-AES256-SHA",
    "DHE-RSA-AES256-SHA",
    "AES128-GCM-SHA256",
    "AES256-GCM-SHA384",
    "AES128-SHA256",
    "AES256-SHA256",
    "AES128-SHA",
    "AES256-SHA",
    "AES",
    "CAMELLIA",
    "!3DES",
    "!aNULL",
    "!eNULL",
    "!EXPORT",
    "!DES",
    "!RC4",
    "!MD5",
    "!PSK",
    "!aECDH",
    "!EDH-DSS-DES-CBC3-SHA",
    "!EDH-RSA-DES-CBC3-SHA",
    "!KRB5-DES-CBC3-SHA",
]


def write_config(filename, **kwargs):
    with open(filename + ".jnj") as f:
        template = jinja2.Template(f.read())
    rendered = template.render(kwargs)

    with open(filename, "w") as f:
        f.write(rendered)


def generate_nginx_config(config):
    """
    Generates nginx config from the app config.
    """
    config = config or {}
    use_https = os.path.exists(os.path.join(QUAYCONF_DIR, "stack/ssl.key"))
    v1_only_domain = config.get("V1_ONLY_DOMAIN", None)
    enable_rate_limits = config.get("FEATURE_RATE_LIMITS", False)
    ssl_protocols = config.get("SSL_PROTOCOLS", SSL_PROTOCOL_DEFAULTS)
    ssl_ciphers = config.get("SSL_CIPHERS", SSL_CIPHER_DEFAULTS)

    write_config(
        os.path.join(QUAYCONF_DIR, "nginx/nginx.conf"),
        use_https=use_https,
        enable_rate_limits=enable_rate_limits,
        v1_only_domain=v1_only_domain,
        ssl_protocols=ssl_protocols,
        ssl_ciphers=":".join(ssl_ciphers),
    )


def generate_server_config(config):
    """
    Generates server config from the app config.
    """
    config = config or {}
    tuf_server = config.get("TUF_SERVER", None)
    tuf_host = config.get("TUF_HOST", None)
    signing_enabled = config.get("FEATURE_SIGNING", False)
    maximum_layer_size = config.get("MAXIMUM_LAYER_SIZE", "20G")
    maximum_cnr_layer_size = config.get("MAXIMUM_CNR_LAYER_SIZE", "1M")
    enable_rate_limits = config.get("FEATURE_RATE_LIMITS", False)

    write_config(
        os.path.join(QUAYCONF_DIR, "nginx/server-base.conf"),
        tuf_server=tuf_server,
        tuf_host=tuf_host,
        signing_enabled=signing_enabled,
        maximum_layer_size=maximum_layer_size,
        maximum_cnr_layer_size=maximum_cnr_layer_size,
        enable_rate_limits=enable_rate_limits,
        static_dir=STATIC_DIR,
    )


def generate_rate_limiting_config(config):
    """
    Generates rate limiting config from the app config.
    """
    config = config or {}
    non_rate_limited_namespaces = config.get("NON_RATE_LIMITED_NAMESPACES") or set()
    enable_rate_limits = config.get("FEATURE_RATE_LIMITS", False)
    write_config(
        os.path.join(QUAYCONF_DIR, "nginx/rate-limiting.conf"),
        non_rate_limited_namespaces=non_rate_limited_namespaces,
        enable_rate_limits=enable_rate_limits,
        static_dir=STATIC_DIR,
    )


def generate_hosted_http_base_config(config):
    """
    Generates hosted http base config from the app config.
    """
    config = config or {}
    feature_proxy_protocol = config.get("FEATURE_PROXY_PROTOCOL", False)

    write_config(
        os.path.join(QUAYCONF_DIR, "nginx/hosted-http-base.conf"),
        feature_proxy_protocol=feature_proxy_protocol,
    )


if __name__ == "__main__":
    if os.path.exists(os.path.join(QUAYCONF_DIR, "stack/config.yaml")):
        with open(os.path.join(QUAYCONF_DIR, "stack/config.yaml"), "r") as f:
            config = yaml.safe_load(f)
    else:
        config = None

    generate_hosted_http_base_config(config)
    generate_rate_limiting_config(config)
    generate_server_config(config)
    generate_nginx_config(config)
