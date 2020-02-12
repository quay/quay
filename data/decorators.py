def deprecated_model(model_cls):
    """ Marks a model has deprecated, and ensures no writings occur on it. """
    model_cls.__deprecated_model = True
    return model_cls
