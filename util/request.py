import os

from flask import request


def get_request_ip():
    """
    Returns the IP address of the client making the current Flask request or None if none.
    """
    remote_addr = request.remote_addr or None
    if os.getenv("TEST", "false").lower() == "true":
        remote_addr = request.headers.get("X-Override-Remote-Addr-For-Testing", remote_addr)

    return remote_addr
