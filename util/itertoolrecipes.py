from itertools import islice

# From: https://docs.python.org/2/library/itertools.html
def take(n, iterable):
    """
    Return first n items of the iterable as a list.
    """
    return list(islice(iterable, n))
