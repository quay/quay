from flask import request

from app import app
from auth.auth_context import determine_auth_type_and_performer_kind
from data.logs_model import logs_model
from util.request import sanitize_request_url


def log_action(kind, user_or_orgname, metadata=None, repo=None, performer=None):
    if not metadata:
        metadata = {}

    # Extended logging fields (opt-in via FEATURE_EXTENDED_ACTION_LOGGING)
    extended_params = {}
    if app.config.get("FEATURE_EXTENDED_ACTION_LOGGING", False):
        # Use shared helper for consistent auth detection across all logging paths
        auth_type, performer_kind = determine_auth_type_and_performer_kind()

        # Capture user agent
        user_agent = None
        if request.user_agent:
            user_agent = request.user_agent.string

        # Get request ID if available (set by RequestWithId class in app.py)
        request_id = getattr(request, "request_id", None)

        # Get X-Forwarded-For header for original client IP behind proxies
        x_forwarded_for = request.headers.get("X-Forwarded-For")

        extended_params = {
            "request_url": sanitize_request_url(request.url),
            "http_method": request.method,
            "auth_type": auth_type,
            "user_agent": user_agent,
            "performer_kind": performer_kind,
            "request_id": request_id,
            "x_forwarded_for": x_forwarded_for,
        }

    logs_model.log_action(
        kind,
        user_or_orgname,
        repository=repo,
        performer=performer,
        ip=request.remote_addr or None,
        metadata=metadata,
        **extended_params,
    )
