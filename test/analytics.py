class FakeMixpanel(object):
    def track(*args, **kwargs):
        pass


def init_app(app):
    return FakeMixpanel()
