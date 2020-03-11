import urllib.request, urllib.parse, urllib.error
import re

from text_unidecode import unidecode

from uuid import uuid4

REPOSITORY_NAME_REGEX = re.compile(r"^[a-z0-9][\.a-z0-9_-]{0,254}$")

VALID_TAG_PATTERN = r"[\w][\w.-]{0,127}"
FULL_TAG_PATTERN = r"^[\w][\w.-]{0,127}$"

TAG_REGEX = re.compile(FULL_TAG_PATTERN, re.ASCII)
TAG_ERROR = (
    'Invalid tag: must match [A-Za-z0-9_.-], NOT start with "." or "-", '
    "and can contain 1-128 characters"
)


class ImplicitLibraryNamespaceNotAllowed(Exception):
    """
    Exception raised if the implicit library namespace was specified but is not allowed.
    """

    pass


def escape_tag(tag, default="latest"):
    """
    Escapes a Docker tag, ensuring it matches the tag regular expression.
    """
    if not tag:
        return default

    tag = re.sub(r"^[^\w]", "_", tag)
    tag = re.sub(r"[^\w\.-]", "_", tag)
    return tag[0:127]


def parse_namespace_repository(
    repository, library_namespace, include_tag=False, allow_library=True
):
    repository = unidecode(repository)

    parts = repository.rstrip("/").split("/", 1)
    if len(parts) < 2:
        namespace = library_namespace
        repository = parts[0]
        if not allow_library:
            raise ImplicitLibraryNamespaceNotAllowed()
    else:
        (namespace, repository) = parts

    if include_tag:
        parts = repository.split(":", 1)
        if len(parts) < 2:
            tag = "latest"
        else:
            (repository, tag) = parts

    repository = urllib.parse.quote_plus(repository)
    if include_tag:
        return (namespace, repository, tag)
    return (namespace, repository)


def format_robot_username(parent_username, robot_shortname):
    return "%s+%s" % (parent_username, robot_shortname)


def parse_robot_username(robot_username):
    if not "+" in robot_username:
        return None

    return robot_username.split("+", 2)


def parse_urn(urn):
    """
    Parses a URN, returning a pair that contains a list of URN namespace parts, followed by the
    URN's unique ID.
    """
    if not urn.startswith("urn:"):
        return None

    parts = urn[len("urn:") :].split(":")
    return (parts[0 : len(parts) - 1], parts[len(parts) - 1])


def parse_single_urn(urn):
    """
    Parses a URN, returning a pair that contains the first namespace part, followed by the URN's
    unique ID.
    """
    result = parse_urn(urn)
    if result is None or not len(result[0]):
        return None

    return (result[0][0], result[1])


uuid_generator = lambda: str(uuid4())


def urn_generator(namespace_portions, id_generator=uuid_generator):
    prefix = "urn:%s:" % ":".join(namespace_portions)

    def generate_urn():
        return prefix + id_generator()

    return generate_urn
