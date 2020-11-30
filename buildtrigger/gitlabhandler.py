import os.path
import logging

from calendar import timegm
from functools import wraps

import dateutil.parser
import gitlab
import requests

from jsonschema import validate

from app import app, gitlab_trigger
from buildtrigger.triggerutil import (
    RepositoryReadException,
    TriggerActivationException,
    TriggerDeactivationException,
    TriggerStartException,
    SkipRequestException,
    InvalidPayloadException,
    TriggerAuthException,
    determine_build_ref,
    raise_if_skipped_build,
    find_matching_branches,
)
from buildtrigger.basehandler import BuildTriggerHandler
from endpoints.exception import ExternalServiceError
from util.security.ssh import generate_ssh_keypair
from util.dict_wrappers import JSONPathDict, SafeDictSetter

logger = logging.getLogger(__name__)

GITLAB_WEBHOOK_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "ref": {
            "type": "string",
        },
        "checkout_sha": {
            "type": ["string", "null"],
        },
        "repository": {
            "type": "object",
            "properties": {
                "git_ssh_url": {
                    "type": "string",
                },
            },
            "required": ["git_ssh_url"],
        },
        "commits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                    },
                    "url": {
                        "type": ["string", "null"],
                    },
                    "message": {
                        "type": "string",
                    },
                    "timestamp": {
                        "type": "string",
                    },
                    "author": {
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                            },
                        },
                        "required": ["email"],
                    },
                },
                "required": ["id", "message", "timestamp"],
            },
        },
    },
    "required": ["ref", "checkout_sha", "repository"],
}

_ACCESS_LEVEL_MAP = {
    50: ("owner", True),
    40: ("master", True),
    30: ("developer", False),
    20: ("reporter", False),
    10: ("guest", False),
}

_PER_PAGE_COUNT = 20


def _catch_timeouts_and_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            msg = "Request to the GitLab API timed out"
            logger.exception(msg)
            raise ExternalServiceError(msg)
        except gitlab.GitlabError:
            msg = "GitLab API error. Please contact support."
            logger.exception(msg)
            raise ExternalServiceError(msg)

    return wrapper


def _paginated_iterator(func, exc, **kwargs):
    """
    Returns an iterator over invocations of the given function, automatically handling pagination.
    """
    page = 1
    while True:
        result = func(page=page, per_page=_PER_PAGE_COUNT, **kwargs)
        if result is None or result is False:
            raise exc

        counter = 0
        for item in result:
            yield item
            counter = counter + 1

        if counter < _PER_PAGE_COUNT:
            break

        page = page + 1


def get_transformed_webhook_payload(
    gl_payload, default_branch=None, lookup_user=None, lookup_commit=None
):
    """
    Returns the Gitlab webhook JSON payload transformed into our own payload format.

    If the gl_payload is not valid, returns None.
    """
    try:
        validate(gl_payload, GITLAB_WEBHOOK_PAYLOAD_SCHEMA)
    except Exception as exc:
        raise InvalidPayloadException(exc.message)

    payload = JSONPathDict(gl_payload)

    if payload["object_kind"] != "push" and payload["object_kind"] != "tag_push":
        # Unknown kind of webhook.
        raise SkipRequestException

    # Check for empty commits. The commits list will be empty if the branch is deleted.
    commits = payload["commits"]
    if payload["object_kind"] == "push" and not commits:
        raise SkipRequestException

    # Check for missing commit information.
    commit_sha = payload["checkout_sha"] or payload["after"]
    if commit_sha is None or commit_sha == "0000000000000000000000000000000000000000":
        raise SkipRequestException

    config = SafeDictSetter()
    config["commit"] = commit_sha
    config["ref"] = payload["ref"]
    config["default_branch"] = default_branch
    config["git_url"] = payload["repository.git_ssh_url"]

    found_commit = JSONPathDict({})
    if payload["object_kind"] == "push" or payload["object_kind"] == "tag_push":
        # Find the commit associated with the checkout_sha. Gitlab doesn't (necessary) send this in
        # any order, so we cannot simply index into the commits list.
        found_commit = None
        if commits is not None:
            for commit in commits:
                if commit["id"] == payload["checkout_sha"]:
                    found_commit = JSONPathDict(commit)
                    break

        if found_commit is None and lookup_commit:
            checkout_sha = payload["checkout_sha"] or payload["after"]
            found_commit_info = lookup_commit(payload["project_id"], checkout_sha)
            found_commit = JSONPathDict(dict(found_commit_info) if found_commit_info else {})

        if found_commit is None:
            raise SkipRequestException

    config["commit_info.url"] = found_commit["url"]
    config["commit_info.message"] = found_commit["message"]
    config["commit_info.date"] = found_commit["timestamp"]

    # Note: Gitlab does not send full user information with the payload, so we have to
    # (optionally) look it up.
    author_email = found_commit["author.email"] or found_commit["author_email"]
    if lookup_user and author_email:
        author_info = lookup_user(author_email)
        if author_info:
            config["commit_info.author.username"] = author_info["username"]
            config["commit_info.author.url"] = author_info["html_url"]
            config["commit_info.author.avatar_url"] = author_info["avatar_url"]

    return config.dict_value()


class GitLabBuildTrigger(BuildTriggerHandler):
    """
    BuildTrigger for GitLab.
    """

    @classmethod
    def service_name(cls):
        return "gitlab"

    def _get_authorized_client(self):
        auth_token = self.auth_token or "invalid"
        api_version = self.config.get("API_VERSION", "4")
        client = gitlab.Gitlab(
            gitlab_trigger.api_endpoint(),
            oauth_token=auth_token,
            timeout=20,
            api_version=api_version,
        )
        try:
            client.auth()
        except gitlab.GitlabGetError as ex:
            raise TriggerAuthException(ex.message)
        except gitlab.GitlabAuthenticationError as ex:
            raise TriggerAuthException(ex.message)

        return client

    def is_active(self):
        return "hook_id" in self.config

    @_catch_timeouts_and_errors
    def activate(self, standard_webhook_url):
        config = self.config
        new_build_source = config["build_source"]
        gl_client = self._get_authorized_client()

        # Find the GitLab repository.
        gl_project = gl_client.projects.get(new_build_source)
        if not gl_project:
            msg = "Unable to find GitLab repository for source: %s" % new_build_source
            raise TriggerActivationException(msg)

        # Add a deploy key to the repository.
        public_key, private_key = generate_ssh_keypair()
        config["credentials"] = [
            {
                "name": "SSH Public Key",
                "value": public_key.decode("ascii"),
            },
        ]

        key = gl_project.keys.create(
            {
                "title": "%s Builder" % app.config["REGISTRY_TITLE"],
                "key": public_key.decode("ascii"),
            }
        )

        if not key:
            msg = "Unable to add deploy key to repository: %s" % new_build_source
            raise TriggerActivationException(msg)

        config["key_id"] = key.get_id()

        # Add the webhook to the GitLab repository.
        hook = gl_project.hooks.create(
            {
                "url": standard_webhook_url,
                "push": True,
                "tag_push": True,
                "push_events": True,
                "tag_push_events": True,
            }
        )
        if not hook:
            msg = "Unable to create webhook on repository: %s" % new_build_source
            raise TriggerActivationException(msg)

        config["hook_id"] = hook.get_id()
        self.config = config
        return config, {"private_key": private_key.decode("ascii")}

    def deactivate(self):
        config = self.config
        try:
            gl_client = self._get_authorized_client()
        except TriggerAuthException:
            config.pop("key_id", None)
            config.pop("hook_id", None)
            self.config = config
            return config

        # Find the GitLab repository.
        try:
            gl_project = gl_client.projects.get(config["build_source"])
            if not gl_project:
                config.pop("key_id", None)
                config.pop("hook_id", None)
                self.config = config
                return config
        except gitlab.GitlabGetError as ex:
            if ex.response_code != 404:
                raise

        # Remove the webhook.
        try:
            gl_project.hooks.delete(config["hook_id"])
        except gitlab.GitlabDeleteError as ex:
            if ex.response_code != 404:
                raise

        config.pop("hook_id", None)

        # Remove the key
        try:
            gl_project.keys.delete(config["key_id"])
        except gitlab.GitlabDeleteError as ex:
            if ex.response_code != 404:
                raise

        config.pop("key_id", None)

        self.config = config
        return config

    @_catch_timeouts_and_errors
    def list_build_source_namespaces(self):
        gl_client = self._get_authorized_client()
        current_user = gl_client.user
        if not current_user:
            raise RepositoryReadException("Unable to get current user")

        namespaces = {}
        for namespace in _paginated_iterator(gl_client.namespaces.list, RepositoryReadException):
            namespace_id = namespace.get_id()
            if namespace_id in namespaces:
                namespaces[namespace_id]["score"] = namespaces[namespace_id]["score"] + 1
            else:
                owner = namespace.attributes["name"]
                namespaces[namespace_id] = {
                    "personal": namespace.attributes["kind"] == "user",
                    "id": str(namespace_id),
                    "title": namespace.attributes["name"],
                    "avatar_url": namespace.attributes.get("avatar_url"),
                    "score": 1,
                    "url": namespace.attributes.get("web_url") or "",
                }

        return BuildTriggerHandler.build_namespaces_response(namespaces)

    def _get_namespace(self, gl_client, gl_namespace, lazy=False):
        try:
            if gl_namespace.attributes["kind"] == "group":
                return gl_client.groups.get(gl_namespace.attributes["id"], lazy=lazy)

            if gl_namespace.attributes["kind"] == "user":
                return gl_client.users.get(gl_client.user.attributes["id"], lazy=lazy)

            # Note: This doesn't seem to work for IDs retrieved via the namespaces API; the IDs are
            # different.
            return gl_client.users.get(gl_namespace.attributes["id"], lazy=lazy)
        except gitlab.GitlabGetError:
            return None

    @_catch_timeouts_and_errors
    def list_build_sources_for_namespace(self, namespace_id):
        if not namespace_id:
            return []

        def repo_view(repo):
            # Because *anything* can be None in GitLab API!
            permissions = repo.attributes.get("permissions") or {}
            group_access = permissions.get("group_access") or {}
            project_access = permissions.get("project_access") or {}

            missing_group_access = permissions.get("group_access") is None
            missing_project_access = permissions.get("project_access") is None

            access_level = max(
                group_access.get("access_level") or 0, project_access.get("access_level") or 0
            )

            has_admin_permission = _ACCESS_LEVEL_MAP.get(access_level, ("", False))[1]
            if missing_group_access or missing_project_access:
                # Default to has permission if we cannot check the permissions. This will allow our users
                # to select the repository and then GitLab's own checks will ensure that the webhook is
                # added only if allowed.
                # TODO: Do we want to display this differently in the UI?
                has_admin_permission = True

            view = {
                "name": repo.attributes["path"],
                "full_name": repo.attributes["path_with_namespace"],
                "description": repo.attributes.get("description") or "",
                "url": repo.attributes.get("web_url"),
                "has_admin_permissions": has_admin_permission,
                "private": repo.attributes.get("visibility") == "private",
            }

            if repo.attributes.get("last_activity_at"):
                try:
                    last_modified = dateutil.parser.parse(repo.attributes["last_activity_at"])
                    view["last_updated"] = timegm(last_modified.utctimetuple())
                except ValueError:
                    logger.exception(
                        "Gitlab gave us an invalid last_activity_at: %s", last_modified
                    )

            return view

        gl_client = self._get_authorized_client()

        try:
            gl_namespace = gl_client.namespaces.get(namespace_id)
        except gitlab.GitlabGetError:
            return []

        namespace_obj = self._get_namespace(gl_client, gl_namespace, lazy=True)
        repositories = _paginated_iterator(namespace_obj.projects.list, RepositoryReadException)

        try:
            return BuildTriggerHandler.build_sources_response(
                [repo_view(repo) for repo in repositories]
            )
        except gitlab.GitlabGetError:
            return []

    @_catch_timeouts_and_errors
    def list_build_subdirs(self):
        config = self.config
        gl_client = self._get_authorized_client()
        new_build_source = config["build_source"]

        gl_project = gl_client.projects.get(new_build_source)
        if not gl_project:
            msg = "Unable to find GitLab repository for source: %s" % new_build_source
            raise RepositoryReadException(msg)

        repo_branches = gl_project.branches.list()
        if not repo_branches:
            msg = "Unable to find GitLab branches for source: %s" % new_build_source
            raise RepositoryReadException(msg)

        branches = [branch.attributes["name"] for branch in repo_branches]
        branches = find_matching_branches(config, branches)
        branches = branches or [gl_project.attributes["default_branch"] or "master"]

        repo_tree = gl_project.repository_tree(ref=branches[0])
        if not repo_tree:
            msg = "Unable to find GitLab repository tree for source: %s" % new_build_source
            raise RepositoryReadException(msg)

        return [node["name"] for node in repo_tree if self.filename_is_dockerfile(node["name"])]

    @_catch_timeouts_and_errors
    def load_dockerfile_contents(self):
        gl_client = self._get_authorized_client()
        path = self.get_dockerfile_path()

        gl_project = gl_client.projects.get(self.config["build_source"])
        if not gl_project:
            return None

        branches = self.list_field_values("branch_name")
        branches = find_matching_branches(self.config, branches)
        if branches == []:
            return None

        branch_name = branches[0]
        if gl_project.attributes["default_branch"] in branches:
            branch_name = gl_project.attributes["default_branch"]

        try:
            return gl_project.files.get(path, branch_name).decode()
        except gitlab.GitlabGetError:
            return None

    @_catch_timeouts_and_errors
    def list_field_values(self, field_name, limit=None):
        if field_name == "refs":
            branches = self.list_field_values("branch_name")
            tags = self.list_field_values("tag_name")

            return [{"kind": "branch", "name": b} for b in branches] + [
                {"kind": "tag", "name": t} for t in tags
            ]

        gl_client = self._get_authorized_client()
        gl_project = gl_client.projects.get(self.config["build_source"])
        if not gl_project:
            return []

        if field_name == "tag_name":
            tags = gl_project.tags.list()
            if not tags:
                return []

            if limit:
                tags = tags[0:limit]

            return [tag.attributes["name"] for tag in tags]

        if field_name == "branch_name":
            branches = gl_project.branches.list()
            if not branches:
                return []

            if limit:
                branches = branches[0:limit]

            return [branch.attributes["name"] for branch in branches]

        return None

    def get_repository_url(self):
        return gitlab_trigger.get_public_url(self.config["build_source"])

    @_catch_timeouts_and_errors
    def lookup_commit(self, repo_id, commit_sha):
        if repo_id is None:
            return None

        gl_client = self._get_authorized_client()
        gl_project = gl_client.projects.get(self.config["build_source"], lazy=True)
        commit = gl_project.commits.get(commit_sha)
        if not commit:
            return None

        return commit

    @_catch_timeouts_and_errors
    def lookup_user(self, email):
        gl_client = self._get_authorized_client()
        try:
            result = gl_client.users.list(search=email)
            if not result:
                return None

            [user] = result
            return {
                "username": user.attributes["username"],
                "html_url": user.attributes["web_url"],
                "avatar_url": user.attributes["avatar_url"],
            }
        except ValueError:
            return None

    @_catch_timeouts_and_errors
    def get_metadata_for_commit(self, commit_sha, ref, repo):
        commit = self.lookup_commit(repo.get_id(), commit_sha)
        if commit is None:
            return None

        metadata = {
            "commit": commit.attributes["id"],
            "ref": ref,
            "default_branch": repo.attributes["default_branch"],
            "git_url": repo.attributes["ssh_url_to_repo"],
            "commit_info": {
                "url": os.path.join(repo.attributes["web_url"], "commit", commit.attributes["id"]),
                "message": commit.attributes["message"],
                "date": commit.attributes["committed_date"],
            },
        }

        committer = None
        if "committer_email" in commit.attributes:
            committer = self.lookup_user(commit.attributes["committer_email"])

        author = None
        if "author_email" in commit.attributes:
            author = self.lookup_user(commit.attributes["author_email"])

        if committer is not None:
            metadata["commit_info"]["committer"] = {
                "username": committer["username"],
                "avatar_url": committer["avatar_url"],
                "url": committer.get("http_url", ""),
            }

        if author is not None:
            metadata["commit_info"]["author"] = {
                "username": author["username"],
                "avatar_url": author["avatar_url"],
                "url": author.get("http_url", ""),
            }

        return metadata

    @_catch_timeouts_and_errors
    def manual_start(self, run_parameters=None):
        gl_client = self._get_authorized_client()
        gl_project = gl_client.projects.get(self.config["build_source"])
        if not gl_project:
            raise TriggerStartException("Could not find repository")

        def get_tag_sha(tag_name):
            try:
                tag = gl_project.tags.get(tag_name)
            except gitlab.GitlabGetError:
                raise TriggerStartException("Could not find tag in repository")

            return tag.attributes["commit"]["id"]

        def get_branch_sha(branch_name):
            try:
                branch = gl_project.branches.get(branch_name)
            except gitlab.GitlabGetError:
                raise TriggerStartException("Could not find branch in repository")

            return branch.attributes["commit"]["id"]

        # Find the branch or tag to build.
        (commit_sha, ref) = determine_build_ref(
            run_parameters, get_branch_sha, get_tag_sha, gl_project.attributes["default_branch"]
        )

        metadata = self.get_metadata_for_commit(commit_sha, ref, gl_project)
        return self.prepare_build(metadata, is_manual=True)

    @_catch_timeouts_and_errors
    def handle_trigger_request(self, request):
        payload = request.get_json()
        if not payload:
            raise InvalidPayloadException()

        logger.debug("GitLab trigger payload %s", payload)

        # Lookup the default branch.
        gl_client = self._get_authorized_client()
        gl_project = gl_client.projects.get(self.config["build_source"])
        if not gl_project:
            logger.debug("Skipping GitLab build; project %s not found", self.config["build_source"])
            raise InvalidPayloadException()

        def lookup_commit(repo_id, commit_sha):
            commit = self.lookup_commit(repo_id, commit_sha)
            if commit is None:
                return None

            return dict(commit.attributes)

        default_branch = gl_project.attributes["default_branch"]
        metadata = get_transformed_webhook_payload(
            payload,
            default_branch=default_branch,
            lookup_user=self.lookup_user,
            lookup_commit=lookup_commit,
        )
        prepared = self.prepare_build(metadata)

        # Check if we should skip this build.
        raise_if_skipped_build(prepared, self.config)
        return prepared
