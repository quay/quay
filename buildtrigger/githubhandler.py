import logging
import os.path
import base64
import re

from calendar import timegm
from functools import wraps
from ssl import SSLError

from github import (
    Github,
    UnknownObjectException,
    GithubException,
    BadCredentialsException as GitHubBadCredentialsException,
)

from jsonschema import validate

from app import app, github_trigger
from buildtrigger.triggerutil import (
    RepositoryReadException,
    TriggerActivationException,
    TriggerDeactivationException,
    TriggerStartException,
    EmptyRepositoryException,
    ValidationRequestException,
    SkipRequestException,
    InvalidPayloadException,
    determine_build_ref,
    raise_if_skipped_build,
    find_matching_branches,
)
from buildtrigger.basehandler import BuildTriggerHandler
from endpoints.exception import ExternalServiceError
from util.security.ssh import generate_ssh_keypair
from util.dict_wrappers import JSONPathDict, SafeDictSetter

logger = logging.getLogger(__name__)

GITHUB_WEBHOOK_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "ref": {
            "type": "string",
        },
        "head_commit": {
            "type": ["object", "null"],
            "properties": {
                "id": {
                    "type": "string",
                },
                "url": {
                    "type": "string",
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
                        "username": {"type": "string"},
                        "html_url": {"type": "string"},
                        "avatar_url": {"type": "string"},
                    },
                },
                "committer": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "html_url": {"type": "string"},
                        "avatar_url": {"type": "string"},
                    },
                },
            },
            "required": ["id", "url", "timestamp"],
        },
        "repository": {
            "type": "object",
            "properties": {
                "ssh_url": {
                    "type": "string",
                },
            },
            "required": ["ssh_url"],
        },
    },
    "required": ["ref", "head_commit", "repository"],
}


def get_transformed_webhook_payload(gh_payload, default_branch=None, lookup_user=None):
    """
    Returns the GitHub webhook JSON payload transformed into our own payload format.

    If the gh_payload is not valid, returns None.
    """
    try:
        validate(gh_payload, GITHUB_WEBHOOK_PAYLOAD_SCHEMA)
    except Exception as exc:
        raise InvalidPayloadException(exc.message)

    payload = JSONPathDict(gh_payload)

    if payload["head_commit"] is None:
        raise SkipRequestException

    config = SafeDictSetter()
    config["commit"] = payload["head_commit.id"]
    config["ref"] = payload["ref"]
    config["default_branch"] = payload["repository.default_branch"] or default_branch
    config["git_url"] = payload["repository.ssh_url"]

    config["commit_info.url"] = payload["head_commit.url"]
    config["commit_info.message"] = payload["head_commit.message"]
    config["commit_info.date"] = payload["head_commit.timestamp"]

    config["commit_info.author.username"] = payload["head_commit.author.username"]
    config["commit_info.author.url"] = payload.get("head_commit.author.html_url")
    config["commit_info.author.avatar_url"] = payload.get("head_commit.author.avatar_url")

    config["commit_info.committer.username"] = payload.get("head_commit.committer.username")
    config["commit_info.committer.url"] = payload.get("head_commit.committer.html_url")
    config["commit_info.committer.avatar_url"] = payload.get("head_commit.committer.avatar_url")

    # Note: GitHub doesn't always return the extra information for users, so we do the lookup
    # manually if possible.
    if (
        lookup_user
        and not payload.get("head_commit.author.html_url")
        and payload.get("head_commit.author.username")
    ):
        author_info = lookup_user(payload["head_commit.author.username"])
        if author_info:
            config["commit_info.author.url"] = author_info["html_url"]
            config["commit_info.author.avatar_url"] = author_info["avatar_url"]

    if (
        lookup_user
        and payload.get("head_commit.committer.username")
        and not payload.get("head_commit.committer.html_url")
    ):
        committer_info = lookup_user(payload["head_commit.committer.username"])
        if committer_info:
            config["commit_info.committer.url"] = committer_info["html_url"]
            config["commit_info.committer.avatar_url"] = committer_info["avatar_url"]

    return config.dict_value()


def _catch_ssl_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SSLError as se:
            msg = "Request to the GitHub API failed: %s" % se.message
            logger.exception(msg)
            raise ExternalServiceError(msg)

    return wrapper


class GithubBuildTrigger(BuildTriggerHandler):
    """
    BuildTrigger for GitHub that uses the archive API and buildpacks.
    """

    def _get_client(self):
        """
        Returns an authenticated client for talking to the GitHub API.
        """
        return Github(
            base_url=github_trigger.api_endpoint(),
            login_or_token=self.auth_token if self.auth_token else github_trigger.client_id(),
            password=None if self.auth_token else github_trigger.client_secret(),
            timeout=5,
        )

    @classmethod
    def service_name(cls):
        return "github"

    def is_active(self):
        return "hook_id" in self.config

    def get_repository_url(self):
        source = self.config["build_source"]
        return github_trigger.get_public_url(source)

    @staticmethod
    def _get_error_message(ghe, default_msg):
        if ghe.data.get("errors") and ghe.data["errors"][0].get("message"):
            return ghe.data["errors"][0]["message"]

        return default_msg

    @_catch_ssl_errors
    def activate(self, standard_webhook_url):
        config = self.config
        new_build_source = config["build_source"]
        gh_client = self._get_client()

        # Find the GitHub repository.
        try:
            gh_repo = gh_client.get_repo(new_build_source)
        except UnknownObjectException:
            msg = "Unable to find GitHub repository for source: %s" % new_build_source
            raise TriggerActivationException(msg)

        # Add a deploy key to the GitHub repository.
        public_key, private_key = generate_ssh_keypair()
        config["credentials"] = [
            {
                "name": "SSH Public Key",
                "value": public_key.decode("ascii"),
            },
        ]

        try:
            deploy_key = gh_repo.create_key(
                "%s Builder" % app.config["REGISTRY_TITLE"], public_key.decode("ascii")
            )
            config["deploy_key_id"] = deploy_key.id
        except GithubException as ghe:
            default_msg = "Unable to add deploy key to repository: %s" % new_build_source
            msg = GithubBuildTrigger._get_error_message(ghe, default_msg)
            raise TriggerActivationException(msg)

        # Add the webhook to the GitHub repository.
        webhook_config = {
            "url": standard_webhook_url,
            "content_type": "json",
        }

        try:
            hook = gh_repo.create_hook("web", webhook_config)
            config["hook_id"] = hook.id
            config["master_branch"] = gh_repo.default_branch
        except GithubException as ghe:
            default_msg = "Unable to create webhook on repository: %s" % new_build_source
            msg = GithubBuildTrigger._get_error_message(ghe, default_msg)
            raise TriggerActivationException(msg)

        return config, {"private_key": private_key.decode("ascii")}

    @_catch_ssl_errors
    def deactivate(self):
        config = self.config
        gh_client = self._get_client()

        # Find the GitHub repository.
        try:
            repo = gh_client.get_repo(config["build_source"])
        except UnknownObjectException:
            msg = "Unable to find GitHub repository for source: %s" % config["build_source"]
            raise TriggerDeactivationException(msg)
        except GitHubBadCredentialsException:
            msg = "Unable to access repository to disable trigger"
            raise TriggerDeactivationException(msg)

        # If the trigger uses a deploy key, remove it.
        try:
            if config["deploy_key_id"]:
                deploy_key = repo.get_key(config["deploy_key_id"])
                deploy_key.delete()
        except KeyError:
            # There was no config['deploy_key_id'], thus this is an old trigger without a deploy key.
            pass
        except GithubException as ghe:
            default_msg = "Unable to remove deploy key: %s" % config["deploy_key_id"]
            msg = GithubBuildTrigger._get_error_message(ghe, default_msg)
            raise TriggerDeactivationException(msg)

        # Remove the webhook.
        if "hook_id" in config:
            try:
                hook = repo.get_hook(config["hook_id"])
                hook.delete()
            except GithubException as ghe:
                default_msg = "Unable to remove hook: %s" % config["hook_id"]
                msg = GithubBuildTrigger._get_error_message(ghe, default_msg)
                raise TriggerDeactivationException(msg)

        config.pop("hook_id", None)
        self.config = config
        return config

    @_catch_ssl_errors
    def list_build_source_namespaces(self):
        gh_client = self._get_client()
        usr = gh_client.get_user()

        # Build the full set of namespaces for the user, starting with their own.
        namespaces = {}
        namespaces[usr.login] = {
            "personal": True,
            "id": usr.login,
            "title": usr.name or usr.login,
            "avatar_url": usr.avatar_url,
            "url": usr.html_url,
            "score": usr.plan.private_repos if usr.plan else 0,
        }

        for org in usr.get_orgs():
            organization = org.login if org.login else org.name

            # NOTE: We don't load the organization's html_url nor its plan, because doing
            # so requires loading *each organization* via its own API call in this tight
            # loop, which was massively slowing down the load time for users when setting
            # up triggers.
            namespaces[organization] = {
                "personal": False,
                "id": organization,
                "title": organization,
                "avatar_url": org.avatar_url,
                "url": "",
                "score": 0,
            }

        return BuildTriggerHandler.build_namespaces_response(namespaces)

    @_catch_ssl_errors
    def list_build_sources_for_namespace(self, namespace):
        def repo_view(repo):
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "last_updated": timegm(repo.pushed_at.utctimetuple()) if repo.pushed_at else 0,
                "url": repo.html_url,
                "has_admin_permissions": True,
                "private": repo.private,
            }

        gh_client = self._get_client()
        usr = gh_client.get_user()
        if namespace == usr.login:
            repos = [repo_view(repo) for repo in usr.get_repos(type="owner", sort="updated")]
            return BuildTriggerHandler.build_sources_response(repos)

        try:
            org = gh_client.get_organization(namespace)
            if org is None:
                return []
        except GithubException:
            return []

        repos = [repo_view(repo) for repo in org.get_repos(type="member")]
        return BuildTriggerHandler.build_sources_response(repos)

    @_catch_ssl_errors
    def list_build_subdirs(self):
        config = self.config
        gh_client = self._get_client()
        source = config["build_source"]

        try:
            repo = gh_client.get_repo(source)

            # Find the first matching branch.
            repo_branches = self.list_field_values("branch_name") or []
            branches = find_matching_branches(config, repo_branches)
            branches = branches or [repo.default_branch or "master"]
            default_commit = repo.get_branch(branches[0]).commit
            commit_tree = repo.get_git_tree(default_commit.sha, recursive=True)

            return [
                elem.path
                for elem in commit_tree.tree
                if (
                    elem.type == "blob" and self.filename_is_dockerfile(os.path.basename(elem.path))
                )
            ]
        except GithubException as ghe:
            message = ghe.data.get("message", "Unable to list contents of repository: %s" % source)
            if message == "Branch not found":
                raise EmptyRepositoryException()

            raise RepositoryReadException(message)

    @_catch_ssl_errors
    def load_dockerfile_contents(self):
        config = self.config
        gh_client = self._get_client()
        source = config["build_source"]

        try:
            repo = gh_client.get_repo(source)
        except GithubException as ghe:
            message = ghe.data.get("message", "Unable to list contents of repository: %s" % source)
            raise RepositoryReadException(message)

        path = self.get_dockerfile_path()
        if not path:
            return None

        try:
            file_info = repo.get_contents(path)
        # TypeError is needed because directory inputs cause a TypeError
        except (GithubException, TypeError) as ghe:
            logger.error("got error from trying to find github file %s" % ghe)
            return None

        if file_info is None:
            return None

        if isinstance(file_info, list):
            return None

        content = file_info.content
        if file_info.encoding == "base64":
            content = base64.b64decode(content)
        return content

    @_catch_ssl_errors
    def list_field_values(self, field_name, limit=None):
        if field_name == "refs":
            branches = self.list_field_values("branch_name")
            tags = self.list_field_values("tag_name")

            return [{"kind": "branch", "name": b} for b in branches] + [
                {"kind": "tag", "name": tag} for tag in tags
            ]

        config = self.config
        source = config.get("build_source")
        if source is None:
            return []

        if field_name == "tag_name":
            try:
                gh_client = self._get_client()
                repo = gh_client.get_repo(source)
                gh_tags = repo.get_tags()
                if limit:
                    gh_tags = repo.get_tags()[0:limit]

                return [tag.name for tag in gh_tags]
            except GitHubBadCredentialsException:
                return []
            except GithubException:
                logger.exception(
                    "Got GitHub Exception when trying to list tags for trigger %s", self.trigger.id
                )
                return []

        if field_name == "branch_name":
            try:
                gh_client = self._get_client()
                repo = gh_client.get_repo(source)
                gh_branches = repo.get_branches()
                if limit:
                    gh_branches = repo.get_branches()[0:limit]

                branches = [branch.name for branch in gh_branches]

                if not repo.default_branch in branches:
                    branches.insert(0, repo.default_branch)

                if branches[0] != repo.default_branch:
                    branches.remove(repo.default_branch)
                    branches.insert(0, repo.default_branch)

                return branches
            except GitHubBadCredentialsException:
                return ["master"]
            except GithubException:
                logger.exception(
                    "Got GitHub Exception when trying to list branches for trigger %s",
                    self.trigger.id,
                )
                return ["master"]

        return None

    @classmethod
    def _build_metadata_for_commit(cls, commit_sha, ref, repo):
        try:
            commit = repo.get_commit(commit_sha)
        except GithubException:
            logger.exception("Could not load commit information from GitHub")
            return None

        commit_info = {
            "url": commit.html_url,
            "message": commit.commit.message,
            "date": commit.last_modified,
        }

        if commit.author:
            commit_info["author"] = {
                "username": commit.author.login,
                "avatar_url": commit.author.avatar_url,
                "url": commit.author.html_url,
            }

        if commit.committer:
            commit_info["committer"] = {
                "username": commit.committer.login,
                "avatar_url": commit.committer.avatar_url,
                "url": commit.committer.html_url,
            }

        return {
            "commit": commit_sha,
            "ref": ref,
            "default_branch": repo.default_branch,
            "git_url": repo.ssh_url,
            "commit_info": commit_info,
        }

    @_catch_ssl_errors
    def manual_start(self, run_parameters=None):
        config = self.config
        source = config["build_source"]

        try:
            gh_client = self._get_client()
            repo = gh_client.get_repo(source)
            default_branch = repo.default_branch
        except GithubException as ghe:
            msg = GithubBuildTrigger._get_error_message(ghe, "Unable to start build trigger")
            raise TriggerStartException(msg)

        def get_branch_sha(branch_name):
            try:
                branch = repo.get_branch(branch_name)
                return branch.commit.sha
            except GithubException:
                raise TriggerStartException("Could not find branch in repository")

        def get_tag_sha(tag_name):
            tags = {tag.name: tag for tag in repo.get_tags()}
            if not tag_name in tags:
                raise TriggerStartException("Could not find tag in repository")

            return tags[tag_name].commit.sha

        # Find the branch or tag to build.
        (commit_sha, ref) = determine_build_ref(
            run_parameters, get_branch_sha, get_tag_sha, default_branch
        )

        metadata = GithubBuildTrigger._build_metadata_for_commit(commit_sha, ref, repo)
        return self.prepare_build(metadata, is_manual=True)

    @_catch_ssl_errors
    def lookup_user(self, username):
        try:
            gh_client = self._get_client()
            user = gh_client.get_user(username)
            return {"html_url": user.html_url, "avatar_url": user.avatar_url}
        except GithubException:
            return None

    @_catch_ssl_errors
    def handle_trigger_request(self, request):
        # Check the payload to see if we should skip it based on the lack of a head_commit.
        payload = request.get_json()
        if payload is None:
            raise InvalidPayloadException("Missing payload")

        # This is for GitHub's probing/testing.
        if "zen" in payload:
            raise SkipRequestException()

        # Lookup the default branch for the repository.
        if "repository" not in payload:
            raise InvalidPayloadException("Missing 'repository' on request")

        if "owner" not in payload["repository"]:
            raise InvalidPayloadException("Missing 'owner' on repository")

        if "name" not in payload["repository"]["owner"]:
            raise InvalidPayloadException("Missing owner 'name' on repository")

        if "name" not in payload["repository"]:
            raise InvalidPayloadException("Missing 'name' on repository")

        default_branch = None
        lookup_user = None
        try:
            repo_full_name = "%s/%s" % (
                payload["repository"]["owner"]["name"],
                payload["repository"]["name"],
            )

            gh_client = self._get_client()
            repo = gh_client.get_repo(repo_full_name)
            default_branch = repo.default_branch
            lookup_user = self.lookup_user
        except GitHubBadCredentialsException:
            logger.exception("Got GitHub Credentials Exception; Cannot lookup default branch")
        except GithubException:
            logger.exception(
                "Got GitHub Exception when trying to start trigger %s", self.trigger.id
            )
            raise SkipRequestException()

        logger.debug("GitHub trigger payload %s", payload)
        metadata = get_transformed_webhook_payload(
            payload, default_branch=default_branch, lookup_user=lookup_user
        )
        prepared = self.prepare_build(metadata)

        # Check if we should skip this build.
        raise_if_skipped_build(prepared, self.config)
        return prepared
