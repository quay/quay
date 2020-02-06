from collections import namedtuple


class Repository(namedtuple("Repository", ["namespace_name", "name"])):
    """
    Repository represents a repository.
    """


class Notification(
    namedtuple(
        "Notification",
        [
            "uuid",
            "event_name",
            "method_name",
            "event_config_dict",
            "method_config_dict",
            "repository",
        ],
    )
):
    """
    Notification represents a registered notification of some kind.
    """
