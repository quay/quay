def deprecated_model(model_cls):
    """ Marks a model has deprecated, and ensures no writings occur on it. """
    model_cls.__deprecated_model = True
    return model_cls


def is_deprecated_model(model_cls):
    """ Returns whether the given model class has been deprecated. """
    return hasattr(model_cls, "__deprecated_model")
