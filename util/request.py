import os
from functools import wraps

from flask import request
from flask_restful.utils.cors import crossdomain
from app import app

# Base headers that are allowed for cross origin requests
BASE_CROSS_DOMAIN_HEADERS = ["Authorization", "Content-Type", "X-Requested-With"]

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


def crossorigin(anonymous=True):
    cors_methods = ["GET", "HEAD", "OPTIONS", "POST", "DELETE"]

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cors_origin = app.config.get("CORS_ORIGIN", "*")
            headers = BASE_CROSS_DOMAIN_HEADERS

            # For calls that can only be called from
            # a known cross-origin domain like CSRF token
            # request
            if not anonymous and cors_origin == "*":
                return func(*args, **kwargs)

            credentials = False
            if cors_origin != "*":
                headers = BASE_CROSS_DOMAIN_HEADERS + SINGLE_ORIGIN_CROSS_DOMAIN_HEADERS
                # for single origin requests, allow cookies
                credentials = True

            decorator = crossdomain(
                origin=cors_origin, methods=cors_methods, headers=headers, credentials=credentials
            )
            return decorator(func)(*args, **kwargs)

        return wrapper

    return decorate
