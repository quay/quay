from raven.contrib.flask import Sentry as FlaskSentry


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
            sentry = FlaskSentry(app, register_signal=False)
        else:
            sentry = FakeSentry()

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["sentry"] = sentry
        return sentry

    def __getattr__(self, name):
        return getattr(self.state, name, None)
