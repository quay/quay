from werkzeug.routing import BaseConverter

import features


class APIRepositoryPathConverter(BaseConverter):
    """
    Converter for handling repository paths.

    Does not handle library paths.
    """

    def __init__(self, url_map):
        super(APIRepositoryPathConverter, self).__init__(url_map)
        self.weight = 200
        self.regex = r"([^/]+/[^/]+)"


class RepositoryPathConverter(BaseConverter):
    """
    Converter for handling repository paths.

    Handles both library and non-library paths (if configured).
    """

    def __init__(self, url_map):
        super(RepositoryPathConverter, self).__init__(url_map)
        self.weight = 200

        if features.LIBRARY_SUPPORT:
            # Allow names without namespaces.
            self.regex = r"[^/]+(/[^/]+)?"
        else:
            self.regex = r"([^/]+/[^/]+)"


class RegexConverter(BaseConverter):
    """
    Converter for handling custom regular expression patterns in paths.
    """

    def __init__(self, url_map, regex_value):
        super(RegexConverter, self).__init__(url_map)
        self.regex = regex_value
