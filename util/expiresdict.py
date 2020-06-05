from datetime import datetime

from six import iteritems


class ExpiresEntry(object):
    """
    A single entry under a ExpiresDict.
    """

    def __init__(self, value, expires=None):
        self.value = value
        self._expiration = expires

    @property
    def expired(self):
        if self._expiration is None:
            return False

        return datetime.now() >= self._expiration


class ExpiresDict(object):
    """
    ExpiresDict defines a dictionary-like class whose keys have expiration.

    The rebuilder is a function that returns the full contents of the cached dictionary as a dict of
    the keys and whose values are TTLEntry's. If the rebuilder is None, then no rebuilding is
    performed.
    """

    def __init__(self, rebuilder=None):
        self._rebuilder = rebuilder
        self._items = {}

    def __getitem__(self, key):
        found = self.get(key)
        if found is None:
            raise KeyError

        return found

    def get(self, key, default_value=None):
        # Check the cache first. If the key is found and it has not yet expired,
        # return it.
        found = self._items.get(key)
        if found is not None and not found.expired:
            return found.value

        # Otherwise the key has expired or was not found. Rebuild the cache and check it again.
        items = self._rebuild()
        found_item = items.get(key)
        if found_item is None:
            return default_value

        return found_item.value

    def __contains__(self, key):
        return self.get(key) is not None

    def _rebuild(self):
        if self._rebuilder is None:
            return self._items

        items = self._rebuilder()
        self._items = items
        return items

    def _alive_items(self):
        return {k: entry.value for (k, entry) in list(self._items.items()) if not entry.expired}

    def items(self):
        return list(self._alive_items().items())

    def iteritems(self):
        return iteritems(self._alive_items())

    def __iter__(self):
        return iter(self._alive_items())

    def __delitem__(self, key):
        del self._items[key]

    def __len__(self):
        return len(self._alive_items())

    def set(self, key, value, expires=None):
        self._items[key] = ExpiresEntry(value, expires=expires)

    def __setitem__(self, key, value):
        return self.set(key, value)
