from collections import namedtuple
import features
import re

Scope = namedtuple("scope", ["scope", "icon", "dangerous", "title", "description"])


READ_REPO = Scope(
    scope="repo:read",
    icon="fa-hdd-o",
    dangerous=False,
    title="View all visible repositories",
    description=(
        "This application will be able to view and pull all repositories "
        "visible to the granting user or robot account"
    ),
)

WRITE_REPO = Scope(
    scope="repo:write",
    icon="fa-hdd-o",
    dangerous=False,
    title="Read/Write to any accessible repositories",
    description=(
        "This application will be able to view, push and pull to all "
        "repositories to which the granting user or robot account has "
        "write access"
    ),
)

ADMIN_REPO = Scope(
    scope="repo:admin",
    icon="fa-hdd-o",
    dangerous=False,
    title="Administer Repositories",
    description=(
        "This application will have administrator access to all "
        "repositories to which the granting user or robot account has "
        "access"
    ),
)

CREATE_REPO = Scope(
    scope="repo:create",
    icon="fa-plus",
    dangerous=False,
    title="Create Repositories",
    description=(
        "This application will be able to create repositories in to any "
        "namespaces that the granting user or robot account is allowed "
        "to create repositories"
    ),
)

READ_USER = Scope(
    scope="user:read",
    icon="fa-user",
    dangerous=False,
    title="Read User Information",
    description=(
        "This application will be able to read user information such as "
        "username and email address."
    ),
)

ADMIN_USER = Scope(
    scope="user:admin",
    icon="fa-gear",
    dangerous=True,
    title="Administer User",
    description=(
        "This application will be able to administer your account "
        "including creating robots and granting them permissions "
        "to your repositories. You should have absolute trust in the "
        "requesting application before granting this permission."
    ),
)

ORG_ADMIN = Scope(
    scope="org:admin",
    icon="fa-gear",
    dangerous=True,
    title="Administer Organization",
    description=(
        "This application will be able to administer your organizations "
        "including creating robots, creating teams, adjusting team "
        "membership, and changing billing settings. You should have "
        "absolute trust in the requesting application before granting this "
        "permission."
    ),
)

DIRECT_LOGIN = Scope(
    scope="direct_user_login",
    icon="fa-exclamation-triangle",
    dangerous=True,
    title="Full Access",
    description=(
        "This scope should not be available to OAuth applications. "
        "Never approve a request for this scope!"
    ),
)

SUPERUSER = Scope(
    scope="super:user",
    icon="fa-street-view",
    dangerous=True,
    title="Super User Access",
    description=(
        "This application will be able to administer your installation "
        "including managing users, managing organizations and other "
        "features found in the superuser panel. You should have "
        "absolute trust in the requesting application before granting this "
        "permission."
    ),
)

ALL_SCOPES = {
    scope.scope: scope
    for scope in (
        READ_REPO,
        WRITE_REPO,
        ADMIN_REPO,
        CREATE_REPO,
        READ_USER,
        ORG_ADMIN,
        SUPERUSER,
        ADMIN_USER,
    )
}

IMPLIED_SCOPES = {
    ADMIN_REPO: {ADMIN_REPO, WRITE_REPO, READ_REPO},
    WRITE_REPO: {WRITE_REPO, READ_REPO},
    READ_REPO: {READ_REPO},
    CREATE_REPO: {CREATE_REPO},
    READ_USER: {READ_USER},
    ORG_ADMIN: {ORG_ADMIN},
    SUPERUSER: {SUPERUSER},
    ADMIN_USER: {ADMIN_USER},
    None: set(),
}


def app_scopes(app_config):
    scopes_from_config = dict(ALL_SCOPES)
    if not app_config.get("FEATURE_SUPER_USERS", False):
        del scopes_from_config[SUPERUSER.scope]
    return scopes_from_config


def scopes_from_scope_string(scopes):
    if not scopes:
        scopes = ""

    # Note: The scopes string should be space seperated according to the spec:
    # https://tools.ietf.org/html/rfc6749#section-3.3
    # However, we also support commas for backwards compatibility with existing callers to our code.
    scope_set = {ALL_SCOPES.get(scope, None) for scope in re.split(" |,", scopes)}
    return scope_set if not None in scope_set else set()


def validate_scope_string(scopes):
    decoded = scopes_from_scope_string(scopes)
    return len(decoded) > 0


def is_subset_string(full_string, expected_string):
    """
    Returns true if the scopes found in expected_string are also found in full_string.
    """
    full_scopes = scopes_from_scope_string(full_string)
    if not full_scopes:
        return False

    full_implied_scopes = set.union(*[IMPLIED_SCOPES[scope] for scope in full_scopes])
    expected_scopes = scopes_from_scope_string(expected_string)
    return expected_scopes.issubset(full_implied_scopes)


def get_scope_information(scopes_string):
    scopes = scopes_from_scope_string(scopes_string)
    scope_info = []
    for scope in scopes:
        scope_info.append(
            {
                "title": scope.title,
                "scope": scope.scope,
                "description": scope.description,
                "icon": scope.icon,
                "dangerous": scope.dangerous,
            }
        )

    return scope_info
