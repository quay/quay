# NOTE: This objects are used directly in the external-notification-data and vulnerability-service
# on the frontend, so be careful with changing their existing keys.
PRIORITY_LEVELS = {
    "Unknown": {
        "title": "Unknown",
        "value": "Unknown",
        "index": 6,
        "level": "info",
        "color": "#9B9B9B",
        "score": 0,
        "description": "Unknown is either a security problem that has not been assigned to a priority"
        + " yet or a priority that our system did not recognize",
        "banner_required": False,
    },
    "Negligible": {
        "title": "Negligible",
        "value": "Negligible",
        "index": 5,
        "level": "info",
        "color": "#9B9B9B",
        "score": 1,
        "description": "Negligible is technically a security problem, but is only theoretical "
        + "in nature, requires a very special situation, has almost no install base, "
        + "or does no real damage.",
        "banner_required": False,
    },
    "Low": {
        "title": "Low",
        "value": "Low",
        "index": 4,
        "level": "warning",
        "color": "#F8CA1C",
        "score": 3,
        "description": "Low is a security problem, but is hard to exploit due to environment, "
        + "requires a user-assisted attack, a small install base, or does very little"
        + " damage.",
        "banner_required": False,
    },
    "Medium": {
        "title": "Medium",
        "value": "Medium",
        "index": 3,
        "level": "warning",
        "color": "#FCA657",
        "score": 6,
        "description": "Medium is a real security problem, and is exploitable for many people. "
        + "Includes network daemon denial of service attacks, cross-site scripting, and "
        + "gaining user privileges.",
        "banner_required": False,
    },
    "High": {
        "title": "High",
        "value": "High",
        "index": 2,
        "level": "warning",
        "color": "#F77454",
        "score": 9,
        "description": "High is a real problem, exploitable for many people in a default "
        + "installation. Includes serious remote denial of services, local root "
        + "privilege escalations, or data loss.",
        "banner_required": False,
    },
    "Critical": {
        "title": "Critical",
        "value": "Critical",
        "index": 1,
        "level": "error",
        "color": "#D64456",
        "score": 10,
        "description": "Critical is a world-burning problem, exploitable for nearly all people in "
        + "a installation of the package. Includes remote root privilege escalations, "
        + "or massive data loss.",
        "banner_required": False,
    },
    "Defcon1": {
        "title": "Defcon 1",
        "value": "Defcon1",
        "index": 0,
        "level": "error",
        "color": "black",
        "score": 11,
        "description": "Defcon1 is a Critical problem which has been manually highlighted by the Quay"
        + " team. It requires immediate attention.",
        "banner_required": True,
    },
}


def get_priority_for_index(index):
    try:
        int_index = int(index)
    except ValueError:
        return "Unknown"

    for priority in PRIORITY_LEVELS:
        if PRIORITY_LEVELS[priority]["index"] == int_index:
            return priority

    return "Unknown"
