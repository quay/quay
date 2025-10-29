import logging

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration

# Note: Imported inside functions to avoid circular imports where possible

logger = logging.getLogger(__name__)


def _sentry_before_send_ignore_known(ex_event, hint):
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
    try:
        exc_info = hint.get("exc_info") if isinstance(hint, dict) else None
        if exc_info is not None and len(exc_info) >= 1:
            exc_type = exc_info[0]
            # Compare by class name to avoid import-time cycles; fall back to isinstance if safe
            name = getattr(exc_type, "__name__", "")
            if name in {"InvalidBearerTokenException", "InvalidJWTException"}:
                return None
        # Also check mechanism-embedded exception if available
        mechanism = (ex_event or {}).get("exception", {}).get("values", [])
        if mechanism:
            ty = mechanism[0].get("type")
            if ty in {"InvalidBearerTokenException", "InvalidJWTException"}:
                return None

        # Check for HTTP client errors (4xx status codes)
        if ex_event and "request" in ex_event:
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

                    # Check for 4xx in exception values
                    if mechanism:
                        for exc in mechanism:
                            if "value" in exc:
                                exc_value = str(exc["value"])
                                # Check for common 4xx error patterns
                                if any(
                                    pattern in exc_value.lower()
                                    for pattern in [
                                        "400",
                                        "401",
                                        "403",
                                        "404",
                                        "unauthorized",
                                        "forbidden",
                                        "not found",
                                        "bad request",
                                        "client error",
                                    ]
                                ):
                                    return None

        # Check for network-related errors
        if mechanism:
            for exc in mechanism:
                exc_value = str(exc.get("value", "")).lower()
                exc_type = exc.get("type", "").lower()

                # Network error patterns
                if any(
                    pattern in exc_value or pattern in exc_type
                    for pattern in [
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
                ):
                    return None

        # Check for CSRF token related errors
        if mechanism:
            for exc in mechanism:
                exc_value = str(exc.get("value", "")).lower()
                if any(
                    pattern in exc_value
                    for pattern in [
                        "csrf",
                        "invalid token",
                        "token mismatch",
                        "forbidden (csrf token missing)",
                        "session expired",
                        "authentication required",
                    ]
                ):
                    return None

        # Check for browser-specific errors
        if ex_event and "platform" in ex_event:
            platform = ex_event.get("platform", "").lower()
            if platform in ["javascript", "browser"]:
                # Filter out common browser errors that are not server-side issues
                if mechanism:
                    for exc in mechanism:
                        exc_value = str(exc.get("value", "")).lower()
                        exc_type = exc.get("type", "").lower()

                        # Common browser errors to filter
                        if any(
                            pattern in exc_value or pattern in exc_type
                            for pattern in [
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
                        ):
                            return None

        # Check for specific error messages that indicate client-side issues
        if mechanism:
            for exc in mechanism:
                exc_value = str(exc.get("value", "")).lower()
                if any(
                    pattern in exc_value
                    for pattern in [
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
                    ]
                ):
                    return None

        # Check for infrastructure/configuration errors that should be filtered
        if mechanism:
            for exc in mechanism:
                exc_value = str(exc.get("value", "")).lower()
                exc_type = exc.get("type", "").lower()

                # Filter out specific noisy connection errors (but keep important ones)
                if any(
                    pattern in exc_value or pattern in exc_type
                    for pattern in [
                        # Security scanner connection errors (noisy, not critical)
                        "security scanner endpoint",
                        "localhost:6000",
                        "clair",
                        "vulnerability scanner",
                        "indexer api",
                        "connection error when trying to connect",
                        # Network errors that are typically client-side
                        "connection aborted",
                        "connection timeout",
                        "request timeout",
                        "errno 111",
                        "connectionrefusederror",
                        # Service unavailable errors for non-critical services
                        "service unavailable",
                        "endpoint not available",
                    ]
                ):
                    return None

                # These will NOT be filtered out:
                # - Database connection errors
                # - Redis connection errors
                # - Critical service connection errors
                # - Authentication service errors

                # Check for important connection errors that should NOT be filtered
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

                # If it's an important service, don't filter it out
                if any(pattern in exc_value for pattern in important_patterns):
                    pass
                else:
                    # Filter out other Quay infrastructure errors
                    if any(
                        pattern in exc_value
                        for pattern in [
                            "security scanner",
                            "clair",
                            "vulnerability scanner",
                            "indexer api",
                            "connection error when trying to connect",
                        ]
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
