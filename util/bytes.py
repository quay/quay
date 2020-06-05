class Bytes(object):
    """
    Wrapper around strings and unicode objects to ensure we are always using the correct encoded or
    decoded data.
    """

    def __init__(self, data):
        assert isinstance(data, bytes)
        self._encoded_data = data

    @classmethod
    def for_string_or_unicode(cls, input):
        # If the string is a unicode string, then encode its data as UTF-8. Note that
        # we don't catch any decode exceptions here, as we want those to be raised.
        if isinstance(input, str):
            return Bytes(input.encode("utf-8"))

        # Next, try decoding as UTF-8. If we have a utf-8 encoded string, then we have no
        # additional conversion to do.
        try:
            input.decode("utf-8")
            return Bytes(input)
        except UnicodeDecodeError:
            pass

        # Finally, if the data is (somehow) a unicode string inside a `str` type, then
        # re-encoded the data.
        return Bytes(input.encode("utf-8"))

    def as_encoded_str(self):
        return self._encoded_data

    def as_unicode(self):
        return self._encoded_data.decode("utf-8")
