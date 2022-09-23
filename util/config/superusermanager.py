from multiprocessing.sharedctypes import Array
from util.validation import MAX_USERNAME_LENGTH


SUPER_USERS_CONFIG = "SUPER_USERS"
RESTRICTED_USERS_WHITELIST_CONFIG = "RESTRICTED_USERS_WHITELIST"


class UserManager(object):
    def __init__(self, app, config_key):
        usernames = app.config.get(config_key, [])
        usernames_str = ",".join(usernames)

        self._max_length = len(usernames_str) + MAX_USERNAME_LENGTH + 1
        self._array = Array("c", self._max_length, lock=True)
        self._array.value = usernames_str.encode("utf8")


class SuperUserManager(UserManager):
    """
    In-memory helper class for quickly accessing (and updating) the valid set of super users.

    This class communicates across processes to ensure that the shared set is always the same.
    """

    def __init__(self, app):
        super().__init__(app, SUPER_USERS_CONFIG)

    def is_superuser(self, username):
        """
        Returns if the given username represents a super user.
        """
        usernames = self._array.value.decode("utf8").split(",")
        return username in usernames

    def register_superuser(self, username):
        """
        Registers a new username as a super user for the duration of the container.

        Note that this does *not* change any underlying config files.
        """
        usernames = self._array.value.decode("utf8").split(",")
        usernames.append(username)
        new_string = ",".join(usernames)

        if len(new_string) <= self._max_length:
            self._array.value = new_string.encode("utf8")
        else:
            raise Exception("Maximum superuser count reached. Please report this to support.")

    def has_superusers(self):
        """
        Returns whether there are any superusers defined.
        """
        return bool(self._array.value)


class RestrictedUserManager(UserManager):
    def __init__(self, app):
        super().__init__(app, RESTRICTED_USERS_WHITELIST_CONFIG)

    def is_restricted(self, username, include_robots=True):
        if include_robots:
            username = username.split("+", 1)[0]

        usernames = self._array.value.decode("utf8").split(",")
        return not (username in usernames)
