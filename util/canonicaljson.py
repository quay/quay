import collections


def canonicalize(json_obj):
    """
    This function canonicalizes a Python object that will be serialized as JSON.

    Args:
      json_obj (object): the Python object that will later be serialized as JSON.

    Returns:
      object: json_obj now sorted to its canonical form.
    """
    if isinstance(json_obj, collections.MutableMapping):
        sorted_obj = sorted({key: canonicalize(val) for key, val in list(json_obj.items())}.items())
        return collections.OrderedDict(sorted_obj)
    elif isinstance(json_obj, (list, tuple)):
        return [canonicalize(val) for val in json_obj]
    return json_obj
