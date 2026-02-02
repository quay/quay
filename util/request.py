import os
from functools import wraps
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from flask import request
from flask_restful.utils.cors import crossdomain

from app import app

# Query parameters that should be redacted from logged URLs for security
SENSITIVE_QUERY_PARAMS = frozenset({
    "token",
    "access_token",
    "refresh_token",
    "code",
    "api_key",
    "apikey",
    "password",
    "secret",
    "credential",
    "signature",
    "sig",
})

# Base headers that are allowed for cross origin requests
BASE_CROSS_DOMAIN_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Requested-With",
]

# Additional headers that are allowed if CORS is restricted to single origin
SINGLE_ORIGIN_CROSS_DOMAIN_HEADERS = ["Cookie", "X-CSRF-Token"]


def get_request_ip():
    """
    Returns the IP address of the client making the current Flask request or None if none.
    """
    remote_addr = request.remote_addr or None
    if os.getenv("TEST", "false").lower() == "true":
        remote_addr = request.headers.get("X-Override-Remote-Addr-For-Testing", remote_addr)

    return remote_addr


def sanitize_request_url(url):
    """
    Sanitizes a URL by redacting sensitive query parameters.

    This prevents tokens, API keys, and other credentials from being logged.
    Parameters in SENSITIVE_QUERY_PARAMS are replaced with '[REDACTED]'.

    Args:
        url: The URL string to sanitize

    Returns:
        The sanitized URL string with sensitive parameters redacted
    """
    if not url or "?" not in url:
        return url

    # Quick check: skip full parsing if no sensitive params present (fast path)
    url_lower = url.lower()
    if not any(param in url_lower for param in SENSITIVE_QUERY_PARAMS):
        return url

    # Slow path: parse and redact
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        sanitized_params = {
            key: ["[REDACTED]"] if key.lower() in SENSITIVE_QUERY_PARAMS else values
            for key, values in params.items()
        }
        sanitized_query = urlencode(sanitized_params, doseq=True)
        return urlunparse(parsed._replace(query=sanitized_query))
    except Exception:
        # If parsing fails, return the original URL rather than failing the log
        return url


def crossorigin(anonymous=True):
    cors_methods = ["GET", "HEAD", "OPTIONS", "POST", "DELETE", "PUT"]

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cors_origin_list = app.config.get("CORS_ORIGIN", [])
            cors_origin = "*"

            if len(cors_origin_list) == 1:
                cors_origin = cors_origin_list[0]
            elif len(cors_origin_list) > 1:
                # if there are multiple CORS_ORIGIN set, then use
                # the Origin header from the request to set the
                # correct Allow-Origin
                request_origin = request.headers.get("Origin")
                if request_origin and request_origin in cors_origin_list:
                    cors_origin = request_origin

            headers = BASE_CROSS_DOMAIN_HEADERS

            # For calls that are not anonymous eg: CSRF token request
            # respond with no CORS headers if CORS_ORIGIN is not set
            if not anonymous and cors_origin == "*":
                return func(*args, **kwargs)

            credentials = False
            # if we have CORS_ORIGIN set to a domain, then add the corresponding
            # CORS headers as allowed headers
            if cors_origin != "*":
                headers = BASE_CROSS_DOMAIN_HEADERS + SINGLE_ORIGIN_CROSS_DOMAIN_HEADERS
                # for single origin requests, allow cookies
                credentials = True

            decorator = crossdomain(
                origin=cors_origin,
                methods=cors_methods,
                headers=headers,
                credentials=credentials,
            )
            return decorator(func)(*args, **kwargs)

        return wrapper

    return decorate
