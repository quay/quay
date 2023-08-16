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


class ConfigUserManager(UserManager):
    """
    In-memory helper class for quickly accessing (and updating) the valid set of super users.

    This class communicates across processes to ensure that the shared set is always the same.
    """

    def __init__(self, app):
        super_usernames = app.config.get(SUPER_USERS_CONFIG, [])
        super_usernames_str = ",".join(super_usernames)

        self._super_max_length = len(super_usernames_str) + MAX_USERNAME_LENGTH + 1
        self._superusers_array = Array("c", self._super_max_length, lock=True)
        self._superusers_array.value = super_usernames_str.encode("utf8")

        restricted_usernames_whitelist = app.config.get(RESTRICTED_USERS_WHITELIST_CONFIG, None)
        if restricted_usernames_whitelist:
            restricted_usernames_whitelist_str = ",".join(restricted_usernames_whitelist)

            self._restricted_max_length = (
                len(restricted_usernames_whitelist_str) + MAX_USERNAME_LENGTH + 1
            )
            self._restricted_users_array = Array("c", self._restricted_max_length, lock=True)
            self._restricted_users_array.value = restricted_usernames_whitelist_str.encode("utf8")
        else:
            self._restricted_users_array = None

        global_readonly_usernames = app.config.get("GLOBAL_READONLY_SUPER_USERS", [])
        global_readonly_usernames_str = ",".join(global_readonly_usernames)

        self._global_readonly_max_length = (
            len(global_readonly_usernames_str) + MAX_USERNAME_LENGTH + 1
        )
        self._global_readonly_array = Array("c", self._global_readonly_max_length, lock=True)
        self._global_readonly_array.value = global_readonly_usernames_str.encode("utf8")

    def is_superuser(self, username: str) -> bool:
        """
        Returns if the given username represents a super user.
        """
        usernames = self._superusers_array.value.decode("utf8").split(",")
        return username in usernames

    def register_superuser(self, username: str) -> None:
        """
        Registers a new username as a super user for the duration of the container.

        Note that this does *not* change any underlying config files.
        """
        usernames = self._superusers_array.value.decode("utf8").split(",")
        usernames.append(username)
        new_string = ",".join(usernames)

        if len(new_string) <= self._max_length:
            self._superusers_array.value = new_string.encode("utf8")
        else:
            raise Exception("Maximum superuser count reached. Please report this to support.")

    def has_superusers(self) -> bool:
        """
        Returns whether there are any superusers defined.
        """
        return bool(self._superusers_array.value)

    def is_restricted_user(self, username: str, include_robots: bool = True) -> bool:
        if include_robots:
            username = username.split("+")[0]

        if self._restricted_users_array:
            usernames = self._restricted_users_array.value.decode("utf8").split(",")
            return not (username in usernames)
        else:
            return True

    def restricted_whitelist_is_set(self):
        return self._restricted_users_array is not None

    def has_restricted_users(self) -> bool:
        """
        Returns whether there are any restricted users defined.
        If whitelist not set, assumes all users are restricted.
        Assumes at least one user always exists. i.e If whitelist not set and no users exist,
        returns True.
        """
        if not self._restricted_users_array or not self._restricted_users_array.value:
            return True

        return bool(self._restricted_users_array.value)

    def is_global_readonly_superuser(self, username: str) -> bool:
        """
        Returns if the given username represents a super user.
        """
        usernames = self._global_readonly_array.value.decode("utf8").split(",")
        return username in usernames

    def has_global_readonly_superusers(self) -> bool:
        """
        Returns if the given username represents a super user.
        """
        return bool(self._global_readonly_array.value)
