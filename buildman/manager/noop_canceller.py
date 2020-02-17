class NoopCanceller(object):
    """
    A class that can not cancel a build.
    """

    def __init__(self, config=None):
        pass

    def try_cancel_build(self, uuid):
        """
        Does nothing and fails to cancel build.
        """
        return False
