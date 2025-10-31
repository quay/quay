import logging
from typing import Any, Optional

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration

# Note: Imported inside functions to avoid circular imports where possible

logger = logging.getLogger(__name__)


def _sentry_before_send_ignore_known(ex_event: Any, hint: Any) -> Optional[Any]:
    """
    Drop events for expected client-side errors that we don't want in Sentry.

    Specifically ignore:
    - Auth token errors (InvalidBearerTokenException, InvalidJWTException)
    - HTTP 4xx client errors (400, 401, 403, 404, etc.)
    - Network errors (ERR_NETWORK, ECONNABORTED, ETIMEDOUT, ERR_CANCELED)
    - Browser/JavaScript errors from frontend
    - CSRF token related errors
    - Session expiration errors
    """
    if not ex_event:
        return ex_event

    try:
        # Check exception info from hint
        exc_info = hint.get("exc_info") if isinstance(hint, dict) else None
        if exc_info is not None and len(exc_info) >= 1:
            exc_type = exc_info[0]
            # Compare by class name to avoid import-time cycles; fall back to isinstance if safe
            name = getattr(exc_type, "__name__", "")
            if name in {"InvalidBearerTokenException", "InvalidJWTException"}:
                return None

        # Get exception mechanism-embedded exceptions
        mechanism = ex_event.get("exception", {}).get("values", [])

        # Define important patterns that should NOT be filtered out
        important_patterns = [
            "database",
            "postgresql",
            "mysql",
            "redis",
            "auth",
            "authentication",
            "ldap",
            "oauth",
            "jwt",
            "token",
            "session",
            "user",
            "login",
        ]

        # Check exception mechanism in a single loop for efficiency
        if mechanism:
            for exc in mechanism:
                exc_value = str(exc.get("value", "")).lower()
                exc_type_str = exc.get("type", "").lower()

                # First check: Ensure important errors are NOT filtered
                if any(pattern in exc_value for pattern in important_patterns):
                    # Important error, don't filter - continue to next exception
                    continue

                # Check for auth token exceptions
                if exc_type_str in {"InvalidBearerTokenException", "InvalidJWTException"}:
                    return None

                # Check for network-related errors
                network_patterns = [
                    "err_network",
                    "err_canceled",
                    "econnaborted",
                    "etimedout",
                    "err_fr_too_many_redirects",
                    "network error",
                    "connection aborted",
                    "connection timeout",
                    "request timeout",
                    "fetch failed",
                ]
                if any(
                    pattern in exc_value or pattern in exc_type_str for pattern in network_patterns
                ):
                    return None

                # Check for CSRF token related errors
                csrf_patterns = [
                    "csrf",
                    "invalid token",
                    "token mismatch",
                    "forbidden (csrf token missing)",
                    "session expired",
                    "authentication required",
                ]
                if any(pattern in exc_value for pattern in csrf_patterns):
                    return None

                # Check for client-side error messages
                client_error_patterns = [
                    "unauthorized",
                    "forbidden",
                    "not found",
                    "bad request",
                    "method not allowed",
                    "not acceptable",
                    "conflict",
                    "gone",
                    "precondition failed",
                    "request entity too large",
                    "request uri too long",
                    "unsupported media type",
                    "requested range not satisfiable",
                    "expectation failed",
                    "400",
                    "401",
                    "403",
                    "404",
                ]
                if any(pattern in exc_value for pattern in client_error_patterns):
                    return None

                # Check for noisy infrastructure errors (but skip if important service)
                noisy_infrastructure_patterns = [
                    "security scanner endpoint",
                    "localhost:6000",
                    "clair",
                    "vulnerability scanner",
                    "indexer api",
                    "connection error when trying to connect",
                    "connection aborted",
                    "connection timeout",
                    "request timeout",
                    "errno 111",
                    "connectionrefusederror",
                    "service unavailable",
                    "endpoint not available",
                    "security scanner",
                    "vulnerability scanner",
                ]
                if any(
                    pattern in exc_value or pattern in exc_type_str
                    for pattern in noisy_infrastructure_patterns
                ):
                    return None

        # Check for HTTP client errors (4xx status codes) from browser requests
        if "request" in ex_event:
            request_data = ex_event.get("request", {})
            if "headers" in request_data:
                # Check if this is a client-side request
                headers = request_data.get("headers", {})
                user_agent = headers.get("User-Agent", "").lower()

                # Filter out browser requests with 4xx errors
                if any(
                    browser in user_agent
                    for browser in ["mozilla", "chrome", "safari", "firefox", "edge"]
                ):
                    # Check for 4xx status codes in the event
                    if "tags" in ex_event:
                        status_code = ex_event.get("tags", {}).get("status_code")
                        if status_code and 400 <= status_code < 500:
                            return None

        # Check for browser-specific errors
        if "platform" in ex_event:
            platform = ex_event.get("platform", "").lower()
            if platform in ["javascript", "browser"]:
                # Filter out common browser errors that are not server-side issues
                if mechanism:
                    for exc in mechanism:
                        exc_value = str(exc.get("value", "")).lower()
                        exc_type_str = exc.get("type", "").lower()

                        # First check: Ensure important errors are NOT filtered
                        if any(pattern in exc_value for pattern in important_patterns):
                            continue

                        # Common browser errors to filter
                        browser_error_patterns = [
                            "script error",
                            "syntax error",
                            "reference error",
                            "type error",
                            "cannot read property",
                            "undefined is not a function",
                            "network request failed",
                            "failed to fetch",
                            "load failed",
                            "cors error",
                            "cross-origin",
                            "blocked by client",
                        ]
                        if any(
                            pattern in exc_value or pattern in exc_type_str
                            for pattern in browser_error_patterns
                        ):
                            return None

    except Exception:
        # Never break error reporting from the filter
        pass
    return ex_event


import features


class FakeSentryClient(object):
    def captureException(self, *args, **kwargs):
        pass

    def user_context(self, *args, **kwargs):
        pass


class FakeSentry(object):
    def __init__(self):
        self.client = FakeSentryClient()


class Sentry(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        sentry_type = app.config.get("EXCEPTION_LOG_TYPE", "FakeSentry")

        if sentry_type == "Sentry":
            sentry_dsn = app.config.get("SENTRY_DSN", "")
            if sentry_dsn:
                try:
                    logger.info("Initializing Sentry with DSN: %s...", sentry_dsn[:10])

                    integrations = []

                    # Always include logging integration
                    integrations.append(
                        LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
                    )

                    # Only add Flask and SQLAlchemy integrations if OpenTelemetry is not enabled
                    # to avoid conflicts with OpenTelemetry instrumentors
                    if not getattr(features, "OTEL_TRACING", False):
                        integrations.extend(
                            [
                                FlaskIntegration(transaction_style="endpoint"),
                                SqlalchemyIntegration(),
                                StdlibIntegration(),
                            ]
                        )
                        logger.info(
                            "Sentry initialized with full integrations (Flask, SQLAlchemy, Stdlib)"
                        )
                    else:
                        # When OTEL is enabled, use minimal integrations to avoid conflicts
                        logger.info("OpenTelemetry enabled - using minimal Sentry integrations")

                    initialized_sentry = sentry_sdk.init(
                        dsn=sentry_dsn,
                        environment=app.config.get("SENTRY_ENVIRONMENT", "production"),
                        traces_sample_rate=app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.1),
                        profiles_sample_rate=app.config.get("SENTRY_PROFILES_SAMPLE_RATE", 0.1),
                        integrations=integrations,
                        default_integrations=False,
                        auto_session_tracking=True,
                        before_send=_sentry_before_send_ignore_known,
                    )
                    # Return the initialized Sentry SDK object directly
                    sentry = initialized_sentry

                    logger.info("Sentry initialization completed successfully")

                except Exception as e:
                    logger.error("Failed to initialize Sentry: %s", str(e), exc_info=True)
                    sentry = FakeSentry()
            else:
                sentry = FakeSentry()
        else:
            sentry = FakeSentry()

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["sentry"] = sentry
        return sentry

    def __getattr__(self, name):
        if self.state is None:
            return None
        return getattr(self.state, name, None)
