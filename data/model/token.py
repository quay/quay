import logging

from peewee import JOIN

from data.database import (
    AccessToken,
    AccessTokenKind,
    Repository,
    Namespace,
    Role,
    RepositoryBuildTrigger,
)
from data.model import DataModelException, _basequery, InvalidTokenException


logger = logging.getLogger(__name__)


ACCESS_TOKEN_NAME_PREFIX_LENGTH = 32
ACCESS_TOKEN_CODE_MINIMUM_LENGTH = 32


def create_access_token(repo, role, kind=None, friendly_name=None):
    role = Role.get(Role.name == role)
    kind_ref = None
    if kind is not None:
        kind_ref = AccessTokenKind.get(AccessTokenKind.name == kind)

    new_token = AccessToken.create(
        repository=repo, temporary=True, role=role, kind=kind_ref, friendly_name=friendly_name
    )

    return new_token


def create_delegate_token(namespace_name, repository_name, friendly_name, role="read"):
    read_only = Role.get(name=role)
    repo = _basequery.get_existing_repository(namespace_name, repository_name)
    new_token = AccessToken.create(
        repository=repo, role=read_only, friendly_name=friendly_name, temporary=False
    )

    return new_token


def load_token_data(code):
    """
    Load the permissions for any token by code.
    """
    token_name = code[:ACCESS_TOKEN_NAME_PREFIX_LENGTH]
    token_code = code[ACCESS_TOKEN_NAME_PREFIX_LENGTH:]

    if not token_name or not token_code:
        raise InvalidTokenException("Invalid delegate token code: %s" % code)

    # Try loading by name and then comparing the code.
    assert token_name
    try:
        found = (
            AccessToken.select(AccessToken, Repository, Namespace, Role)
            .join(Role)
            .switch(AccessToken)
            .join(Repository)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .where(AccessToken.token_name == token_name)
            .get()
        )

        assert token_code
        if found.token_code is None or not found.token_code.matches(token_code):
            raise InvalidTokenException("Invalid delegate token code: %s" % code)

        assert len(token_code) >= ACCESS_TOKEN_CODE_MINIMUM_LENGTH
        return found
    except AccessToken.DoesNotExist:
        pass

    raise InvalidTokenException("Invalid delegate token code: %s" % code)


def get_full_token_string(token):
    """
    Returns the full string to use for this token to login.
    """
    assert token.token_name
    token_code = token.token_code.decrypt()
    assert len(token.token_name) == ACCESS_TOKEN_NAME_PREFIX_LENGTH
    assert len(token_code) >= ACCESS_TOKEN_CODE_MINIMUM_LENGTH
    return "%s%s" % (token.token_name, token_code)
