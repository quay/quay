def import_class(module_name, class_name):
    """
    Import a class given the specified module name and class name.
    """
    klass = __import__(module_name)
    class_segments = class_name.split(".")
    for segment in class_segments:
        klass = getattr(klass, segment)
    return klass
