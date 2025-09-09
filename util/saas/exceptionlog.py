import logging

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration

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
                    logger = logging.getLogger(__name__)
                    logger.info("Initializing Sentry with DSN: %s", sentry_dsn[:50] + "...")

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
                        transport=sentry_sdk.transport.make_transport(
                            {
                                "pool_connections": 10,  # Instead of default 1
                                "pool_maxsize": 20,  # Max connections per pool
                                "max_retries": 3,  # Retry failed sends
                            }
                        ),
                    )
                    # Return the initialized Sentry SDK object directly
                    sentry = initialized_sentry

                    logger.info("Sentry initialization completed successfully")

                except Exception as e:
                    logger = logging.getLogger(__name__)
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

    def test_sentry_connection(self):
        """Test the Sentry connection by sending a test message."""
        if self.state is None:
            return False

        if isinstance(self.state, FakeSentry):
            return False

        try:
            sentry_sdk.capture_message("Manual Sentry connection test", level="info")
            logger = logging.getLogger(__name__)
            logger.info("Sentry connection test message sent successfully")
            return True
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error("Sentry connection test failed: %s", str(e))
            return False

    def __getattr__(self, name):
        if self.state is None:
            return None
        return getattr(self.state, name, None)
