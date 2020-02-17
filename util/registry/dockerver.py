import re

from semantic_version import Version

_USER_AGENT_SEARCH_REGEX = re.compile(r"docker\/([0-9]+(?:\.[0-9]+){1,2})")
_EXACT_1_5_USER_AGENT = re.compile(r"^Go 1\.1 package http$")
_ONE_FIVE_ZERO = "1.5.0"


def docker_version(user_agent_string):
    """
    Extract the Docker version from the user agent, taking special care to handle the case of a 1.5
    client requesting an auth token, which sends a broken user agent.

    If we can not positively identify a version, return None.
    """

    # First search for a well defined semver portion in the UA header.
    found_semver = _USER_AGENT_SEARCH_REGEX.search(user_agent_string)
    if found_semver:
        # Docker changed their versioning scheme on Feb 17, 2017 to use date-based versioning:
        # https://github.com/docker/docker/pull/31075

        # This scheme allows for 0s to appear as prefixes in the major or minor portions of the version,
        # which violates semver. Strip them out.
        portions = found_semver.group(1).split(".")
        updated_portions = [(p[:-1].lstrip("0") + p[-1]) for p in portions]
        return Version(".".join(updated_portions), partial=True)

    # Check if we received the very specific header which represents a 1.5 request
    # to the auth endpoints.
    elif _EXACT_1_5_USER_AGENT.match(user_agent_string):
        return Version(_ONE_FIVE_ZERO)

    else:
        return None
