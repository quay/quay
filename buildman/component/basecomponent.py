from autobahn.asyncio.wamp import ApplicationSession


class BaseComponent(ApplicationSession):
    """
    Base class for all registered component sessions in the server.
    """

    def __init__(self, config, **kwargs):
        ApplicationSession.__init__(self, config)
        self.server = None
        self.parent_manager = None
        self.build_logs = None
        self.user_files = None

    def kind(self):
        raise NotImplementedError
