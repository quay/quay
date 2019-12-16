import logging

from functools import wraps

from data import model
from util.http import abort


logger = logging.getLogger(__name__)


def _raise_unauthorized(repository, scopes):
    raise Exception("Unauthorized acces to %s", repository)


def _get_reponame_kwargs(*args, **kwargs):
    return [kwargs["namespace"], kwargs["package_name"]]


def disallow_for_image_repository(get_reponame_method=_get_reponame_kwargs):
    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            namespace_name, repo_name = get_reponame_method(*args, **kwargs)
            image_repo = model.repository.get_repository(
                namespace_name, repo_name, kind_filter="image"
            )
            if image_repo is not None:
                logger.debug("Tried to invoked a CNR method on an image repository")
                abort(
                    405,
                    message="Cannot push an application to an image repository with the same name",
                )
            return func(*args, **kwargs)

        return wrapped

    return wrapper


def require_repo_permission(
    permission_class,
    scopes=None,
    allow_public=False,
    raise_method=_raise_unauthorized,
    get_reponame_method=_get_reponame_kwargs,
):
    def wrapper(func):
        @wraps(func)
        @disallow_for_image_repository(get_reponame_method=get_reponame_method)
        def wrapped(*args, **kwargs):
            namespace_name, repo_name = get_reponame_method(*args, **kwargs)
            logger.debug(
                "Checking permission %s for repo: %s/%s",
                permission_class,
                namespace_name,
                repo_name,
            )
            permission = permission_class(namespace_name, repo_name)
            if permission.can() or (
                allow_public and model.repository.repository_is_public(namespace_name, repo_name)
            ):
                return func(*args, **kwargs)
            repository = namespace_name + "/" + repo_name
            raise_method(repository, scopes)

        return wrapped

    return wrapper
