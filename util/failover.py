import logging

from functools import wraps


logger = logging.getLogger(__name__)


class FailoverException(Exception):
    """
    Exception raised when an operation should be retried by the failover decorator.

    Wraps the exception of the initial failure.
    """

    def __init__(self, exception):
        super(FailoverException, self).__init__()
        self.exception = exception


def failover(func):
    """Wraps a function such that it can be retried on specified failures.
    Raises FailoverException when all failovers are exhausted.
    Example:

    @failover
    def get_google(scheme, use_www=False):
      www = 'www.' if use_www else ''
      try:
        r = requests.get(scheme + '://' + www + 'google.com')
      except requests.RequestException as ex:
        raise FailoverException(ex)
      return r

    def GooglePingTest():
      r = get_google(
        (('http'), {'use_www': False}),
        (('http'), {'use_www': True}),
        (('https'), {'use_www': False}),
        (('https'), {'use_www': True}),
      )
      print('Successfully contacted ' + r.url)
    """

    @wraps(func)
    def wrapper(*args_sets):
        for arg_set in args_sets:
            try:
                return func(*arg_set[0], **arg_set[1])
            except FailoverException as ex:
                logger.debug("failing over")
                exception = ex.exception
                continue
        raise exception

    return wrapper
