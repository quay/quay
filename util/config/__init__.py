class URLSchemeAndHostname:
    """
    Immutable configuration for a given preferred url scheme (e.g. http or https), and a hostname
    (e.g. localhost:5000)
    """

    def __init__(self, url_scheme, hostname):
        self._url_scheme = url_scheme
        self._hostname = hostname

    @classmethod
    def from_app_config(cls, app_config):
        """
        Helper method to instantiate class from app config, a frequent pattern.

        :param app_config:
        :return:
        """
        return cls(app_config["PREFERRED_URL_SCHEME"], app_config["SERVER_HOSTNAME"])

    @property
    def url_scheme(self):
        return self._url_scheme

    @property
    def hostname(self):
        return self._hostname

    def get_url(self):
        """
        Returns the application's URL, based on the given url scheme and hostname.
        """
        return "%s://%s" % (self._url_scheme, self._hostname)
