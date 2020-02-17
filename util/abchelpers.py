class NoopIsANoopException(TypeError):
    """
    Raised if the nooper decorator is unnecessary on a class.
    """

    pass


def nooper(cls):
    """
    Decorates a class that derives from an ABCMeta, filling in any unimplemented methods with no-
    ops.
    """

    def empty_func(*args, **kwargs):
        # pylint: disable=unused-argument
        pass

    empty_methods = {m_name: empty_func for m_name in cls.__abstractmethods__}

    if not empty_methods:
        raise NoopIsANoopException("nooper implemented no abstract methods on %s" % cls)

    return type(cls.__name__, (cls,), empty_methods)
