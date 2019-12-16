import json
from jsonpath_rw import parse


class SafeDictSetter(object):
    """
    Specialized write-only dictionary wrapper class that allows for setting nested keys via a path
    syntax.

    Example:
      sds = SafeDictSetter()
      sds['foo.bar.baz'] = 'hello' # Sets 'foo' = {'bar': {'baz': 'hello'}}
      sds['somekey'] = None # Does not set the key since the value is None
    """

    def __init__(self, initial_object=None):
        self._object = initial_object or {}

    def __setitem__(self, path, value):
        self.set(path, value)

    def set(self, path, value, allow_none=False):
        """
        Sets the value of the given path to the given value.
        """
        if value is None and not allow_none:
            return

        pieces = path.split(".")
        current = self._object

        for piece in pieces[: len(pieces) - 1]:
            current_obj = current.get(piece, {})
            if not isinstance(current_obj, dict):
                raise Exception("Key %s is a non-object value: %s" % (piece, current_obj))

            current[piece] = current_obj
            current = current_obj

        current[pieces[-1]] = value

    def dict_value(self):
        """
        Returns the dict value built.
        """
        return self._object

    def json_value(self):
        """
        Returns the JSON string value of the dictionary built.
        """
        return json.dumps(self._object)


class JSONPathDict(object):
    """
    Specialized read-only dictionary wrapper class that uses the jsonpath_rw library to access keys
    via an X-Path-like syntax.

    Example:
      pd = JSONPathDict({'hello': {'hi': 'there'}})
      pd['hello.hi'] # Returns 'there'
    """

    def __init__(self, dict_value):
        """
        Init the helper with the JSON object.
        """
        self._object = dict_value

    def __getitem__(self, path):
        return self.get(path)

    def __iter__(self):
        return iter(self._object.values())

    def iterkeys(self):
        return iter(self._object.keys())

    def get(self, path, not_found_handler=None):
        """
        Returns the value found at the given path.

        Path is a json-path expression.
        """
        if self._object == {} or self._object is None:
            return None
        jsonpath_expr = parse(path)

        try:
            matches = jsonpath_expr.find(self._object)
        except IndexError:
            return None

        if not matches:
            return not_found_handler() if not_found_handler else None

        match = matches[0].value
        if not match:
            return not_found_handler() if not_found_handler else None

        if isinstance(match, dict):
            return JSONPathDict(match)

        return match

    def keys(self):
        return list(self._object.keys())
