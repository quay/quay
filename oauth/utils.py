# Ported to Python 3
# Originally from https://github.com/DeprecatedCode/oauth2lib/blob/d161b010f8a596826050a09e5e94d59443cc12d9/oauth2lib/provider.py

import string
import urllib.parse
from random import SystemRandom

UNICODE_ASCII_CHARACTERS = string.ascii_letters + string.digits


def random_ascii_string(length):
    random = SystemRandom()
    return "".join([random.choice(UNICODE_ASCII_CHARACTERS) for _ in range(length)])


def url_query_params(url):
    """Return query parameters as a dict from the specified URL.

    :param url: URL.
    :type url: str
    :rtype: dict
    """
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query, True))


def url_dequery(url):
    """Return a URL with the query component removed.

    :param url: URL to dequery.
    :type url: str
    :rtype: str
    """
    url = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((url.scheme, url.netloc, url.path, url.params, "", url.fragment))


def build_url(base, additional_params=None):
    """Construct a URL based off of base containing all parameters in
    the query portion of base plus any additional parameters.

    :param base: Base URL
    :type base: str
    ::param additional_params: Additional query parameters to include.
    :type additional_params: dict
    :rtype: str
    """
    url = urllib.parse.urlparse(base)
    query_params = {}
    query_params.update(urllib.parse.parse_qsl(url.query, True))
    if additional_params is not None:
        query_params.update(additional_params)
        for k, v in additional_params.items():
            if v is None:
                query_params.pop(k)

    return urllib.parse.urlunparse(
        (
            url.scheme,
            url.netloc,
            url.path,
            url.params,
            urllib.parse.urlencode(query_params),
            url.fragment,
        )
    )
