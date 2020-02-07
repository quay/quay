def get_app_url(config):
    """
    Returns the application's URL, based on the given config.
    """
    return "%s://%s" % (config["PREFERRED_URL_SCHEME"], config["SERVER_HOSTNAME"])


def slash_join(*args):
    """
    Joins together strings and guarantees there is only one '/' in between the each string joined.

    Double slashes ('//') are assumed to be intentional and are not deduplicated.
    """

    def rmslash(path):
        path = path[1:] if len(path) > 0 and path[0] == "/" else path
        path = path[:-1] if len(path) > 0 and path[-1] == "/" else path
        return path

    args = [rmslash(path) for path in args]
    return "/".join(args)
