from werkzeug.routing import BaseConverter

import features


class APIRepositoryPathConverter(BaseConverter):
    """
    Converter for handling repository paths.

    Does not handle library paths.
    """

    def __init__(self, url_map):
        super().__init__(url_map)
        self.weight = 200
        self.regex = r"([^/]+(/[^/]+)+)"


# TODO(kleesc): Remove after fully deprecating V1 push/pull
class V1CreateRepositoryPathConverter(BaseConverter):
    """
    Converter for handling PUT repository path.
    Handles both library and non-library paths (if configured).

    This is needed so that v1.create_repository does not match possibly
    nested path from other routes.

    For example:
    PUT /repositories/<repopath:repository>/tags/<tag> when no tag is given
    should 404, and not fallback to v1.create_repository route.
    """

    def __init__(self, url_map):
        super().__init__(url_map)
        self.weight = 200

        if features.LIBRARY_SUPPORT:
            # Allow names without namespaces.
            self.regex = r"[^/]+(/[^/]+)*(?<!auth)(?<!tags)(?<!images)"
        else:
            self.regex = r"([^/]+(/[^/]+)+)(?<!auth)(?<!tags)(?<!images)"


class RepositoryPathConverter(BaseConverter):
    """
    Converter for handling repository paths.
    Handles both library and non-library paths (if configured).
    Supports names with or without slashes (nested paths).
    """

    def __init__(self, url_map):
        super().__init__(url_map)
        self.weight = 200

        if features.LIBRARY_SUPPORT:
            # Allow names without namespaces.
            self.regex = r"[^/]+(/[^/]+)*"
        else:
            self.regex = r"([^/]+(/[^/]+)+)"


class RegexConverter(BaseConverter):
    """
    Converter for handling custom regular expression patterns in paths.
    """

    def __init__(self, url_map, regex_value):
        super().__init__(url_map)
        self.regex = regex_value


class RepositoryPathRedirectConverter(BaseConverter):
    """
    Converter for handling redirect paths that don't match any other routes.

    This needs to be separate from RepositoryPathConverter with the updated regex for
    extended repo names support, otherwise, a nonexistent repopath resource would fallback
    to redirecting to the repository web route.

    For example:
    /v2/devtable/testrepo/nested/manifests/somedigest" would previously have (correctly) returned
    a 404, due to the path not matching any routes. With the regex supporting nested path for extended
    repo names, Werkzeug would now (incorrectly) match to redirect to the web page of a repository with
    the above path. See endpoints.web.redirect_to_repository.
    """

    RESERVED_PREFIXES = [
        "v1/",
        "v2/",
        "cnr/",
        "customtrigger/setup/",
        "bitbucket/setup/",
        "repository/",
        "github/callback/trigger/",
        "push/",
    ]

    def __init__(self, url_map):
        super().__init__(url_map)
        self.weight = 200

        if features.LIBRARY_SUPPORT:
            # Allow names without namespaces.
            self.regex = r"(?!{})[^/]+(/[^/]+)*".format(
                "|".join(RepositoryPathRedirectConverter.RESERVED_PREFIXES)
            )
        else:
            self.regex = r"((?!{})[^/]+(/[^/]+)+)".format(
                "|".join(RepositoryPathRedirectConverter.RESERVED_PREFIXES)
            )
