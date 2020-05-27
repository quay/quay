import collections


def canonicalize(json_obj, preserve_sequence_order=True):
    """
    This function canonicalizes a Python object that will be serialized as JSON.
    Example usage: json.dumps(canonicalize(my_obj))

    Args:
      json_obj (object): the Python object that will later be serialized as JSON.

    Returns:
      object: json_obj now sorted to its canonical form.
    """
    if isinstance(json_obj, collections.MutableMapping):
        sorted_obj = sorted(
            {
                key: canonicalize(val, preserve_sequence_order) for key, val in json_obj.items()
            }.items()
        )
        return collections.OrderedDict(sorted_obj)
    elif isinstance(json_obj, (list, tuple)):
        seq = [canonicalize(val, preserve_sequence_order) for val in json_obj]
        return seq if preserve_sequence_order else sorted(seq)

    return json_obj
