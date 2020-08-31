import logging
import os
import re
from calendar import timegm

import dateutil.parser
from bitbucket import BitBucket
from jsonschema import validate

from app import app, get_app_url
from buildtrigger.basehandler import BuildTriggerHandler
from buildtrigger.triggerutil import (
    RepositoryReadException,
    TriggerActivationException,
    TriggerDeactivationException,
    TriggerStartException,
    InvalidPayloadException,
    TriggerProviderException,
    SkipRequestException,
    determine_build_ref,
    raise_if_skipped_build,
    find_matching_branches,
)
from util.dict_wrappers import JSONPathDict, SafeDictSetter
from util.security.ssh import generate_ssh_keypair

logger = logging.getLogger(__name__)

_BITBUCKET_COMMIT_URL = "https://bitbucket.org/%s/commits/%s"
_RAW_AUTHOR_REGEX = re.compile(r".*<(.+)>")

BITBUCKET_WEBHOOK_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "repository": {
            "type": "object",
            "properties": {
                "full_name": {
                    "type": "string",
                },
            },
            "required": ["full_name"],
        },  # /Repository
        "push": {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "new": {
                                "type": "object",
                                "properties": {
                                    "target": {
                                        "type": "object",
                                        "properties": {
                                            "hash": {"type": "string"},
                                            "message": {"type": "string"},
                                            "date": {"type": "string"},
                                            "author": {
                                                "type": "object",
                                                "properties": {
                                                    "user": {
                                                        "type": "object",
                                                        "properties": {
                                                            "display_name": {
                                                                "type": "string",
                                                            },
                                                            "account_id": {
                                                                "type": "string",
                                                            },
                                                            "links": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "avatar": {
                                                                        "type": "object",
                                                                        "properties": {
                                                                            "href": {
                                                                                "type": "string",
                                                                            },
                                                                        },
                                                                        "required": ["href"],
                                                                    },
                                                                },
                                                                "required": ["avatar"],
                                                            },  # /User
                                                        },
                                                    },  # /Author
                                                },
                                            },
                                        },
                                        "required": ["hash", "message", "date"],
                                    },  # /Target
                                },
                                "required": ["name", "target"],
                            },  # /New
                        },
                    },  # /Changes item
                },  # /Changes
            },
            "required": ["changes"],
        },  # / Push
    },
    "actor": {
        "type": "object",
        "properties": {
            "account_id": {
                "type": "string",
            },
            "display_name": {
                "type": "string",
            },
            "links": {
                "type": "object",
                "properties": {
                    "avatar": {
                        "type": "object",
                        "properties": {
                            "href": {
                                "type": "string",
                            },
                        },
                        "required": ["href"],
                    },
                },
                "required": ["avatar"],
            },
        },
    },  # /Actor
    "required": ["push", "repository"],
}  # /Root

BITBUCKET_COMMIT_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "node": {
            "type": "string",
        },
        "message": {
            "type": "string",
        },
        "timestamp": {
            "type": "string",
        },
        "raw_author": {
            "type": "string",
        },
    },
    "required": ["node", "message", "timestamp"],
}


def get_transformed_commit_info(bb_commit, ref, default_branch, repository_name, lookup_author):
    """
    Returns the BitBucket commit information transformed into our own payload format.
    """
    try:
        validate(bb_commit, BITBUCKET_COMMIT_INFO_SCHEMA)
    except Exception as exc:
        logger.exception(
            "Exception when validating Bitbucket commit information: %s from %s",
            exc.message,
            bb_commit,
        )
        raise InvalidPayloadException(exc.message)

    commit = JSONPathDict(bb_commit)

    config = SafeDictSetter()
    config["commit"] = commit["node"]
    config["ref"] = ref
    config["default_branch"] = default_branch
    config["git_url"] = "git@bitbucket.org:%s.git" % repository_name

    config["commit_info.url"] = _BITBUCKET_COMMIT_URL % (repository_name, commit["node"])
    config["commit_info.message"] = commit["message"]
    config["commit_info.date"] = commit["timestamp"]

    match = _RAW_AUTHOR_REGEX.match(commit["raw_author"])
    if match:
        author = lookup_author(match.group(1))
        author_info = JSONPathDict(author) if author is not None else None
        if author_info:
            config["commit_info.author.username"] = author_info["user.display_name"]
            config["commit_info.author.avatar_url"] = author_info["user.avatar"]

    return config.dict_value()


def get_transformed_webhook_payload(bb_payload, default_branch=None):
    """
    Returns the BitBucket webhook JSON payload transformed into our own payload format.

    If the bb_payload is not valid, returns None.
    """
    try:
        validate(bb_payload, BITBUCKET_WEBHOOK_PAYLOAD_SCHEMA)
    except Exception as exc:
        logger.exception(
            "Exception when validating Bitbucket webhook payload: %s from %s",
            exc.message,
            bb_payload,
        )
        raise InvalidPayloadException(exc.message)

    payload = JSONPathDict(bb_payload)
    change = payload["push.changes[-1].new"]
    if not change:
        raise SkipRequestException

    is_branch = change["type"] == "branch"
    ref = "refs/heads/" + change["name"] if is_branch else "refs/tags/" + change["name"]

    repository_name = payload["repository.full_name"]
    target = change["target"]

    config = SafeDictSetter()
    config["commit"] = target["hash"]
    config["ref"] = ref
    config["default_branch"] = default_branch
    config["git_url"] = "git@bitbucket.org:%s.git" % repository_name

    config["commit_info.url"] = target["links.html.href"] or ""
    config["commit_info.message"] = target["message"]
    config["commit_info.date"] = target["date"]

    config["commit_info.author.username"] = target["author.user.display_name"]
    config["commit_info.author.avatar_url"] = target["author.user.links.avatar.href"]

    config["commit_info.committer.username"] = payload["actor.display_name"]
    config["commit_info.committer.avatar_url"] = payload["actor.links.avatar.href"]
    return config.dict_value()


class BitbucketBuildTrigger(BuildTriggerHandler):
    """
    BuildTrigger for Bitbucket.
    """

    @classmethod
    def service_name(cls):
        return "bitbucket"

    def _get_client(self):
        """
        Returns a BitBucket API client for this trigger's config.
        """
        key = app.config.get("BITBUCKET_TRIGGER_CONFIG", {}).get("CONSUMER_KEY", "")
        secret = app.config.get("BITBUCKET_TRIGGER_CONFIG", {}).get("CONSUMER_SECRET", "")

        trigger_uuid = self.trigger.uuid
        callback_url = "%s/oauth1/bitbucket/callback/trigger/%s" % (get_app_url(), trigger_uuid)

        return BitBucket(key, secret, callback_url, timeout=15)

    def _get_authorized_client(self):
        """
        Returns an authorized API client.
        """
        base_client = self._get_client()
        auth_token = self.auth_token or "invalid:invalid"
        token_parts = auth_token.split(":")
        if len(token_parts) != 2:
            token_parts = ["invalid", "invalid"]

        (access_token, access_token_secret) = token_parts
        return base_client.get_authorized_client(access_token, access_token_secret)

    def _get_repository_client(self):
        """
        Returns an API client for working with this config's BB repository.
        """
        source = self.config["build_source"]
        (namespace, name) = source.split("/")
        bitbucket_client = self._get_authorized_client()
        return bitbucket_client.for_namespace(namespace).repositories().get(name)

    def _get_default_branch(self, repository, default_value="master"):
        """
        Returns the default branch for the repository or the value given.
        """
        (result, data, _) = repository.get_main_branch()
        if result:
            return data["name"]

        return default_value

    def get_oauth_url(self):
        """
        Returns the OAuth URL to authorize Bitbucket.
        """
        bitbucket_client = self._get_client()
        (result, data, err_msg) = bitbucket_client.get_authorization_url()
        if not result:
            raise TriggerProviderException(err_msg)

        return data

    def exchange_verifier(self, verifier):
        """
        Exchanges the given verifier token to setup this trigger.
        """
        bitbucket_client = self._get_client()
        access_token = self.config.get("access_token", "")
        access_token_secret = self.auth_token

        # Exchange the verifier for a new access token.
        (result, data, _) = bitbucket_client.verify_token(
            access_token, access_token_secret, verifier
        )
        if not result:
            return False

        # Save the updated access token and secret.
        self.set_auth_token(data[0] + ":" + data[1])

        # Retrieve the current authorized user's information and store the username in the config.
        authorized_client = self._get_authorized_client()
        (result, data, _) = authorized_client.get_current_user()
        if not result:
            return False

        self.put_config_key("account_id", data["user"]["account_id"])
        self.put_config_key("nickname", data["user"]["nickname"])
        return True

    def is_active(self):
        return "webhook_id" in self.config

    def activate(self, standard_webhook_url):
        config = self.config

        # Add a deploy key to the repository.
        public_key, private_key = generate_ssh_keypair()
        config["credentials"] = [
            {
                "name": "SSH Public Key",
                "value": public_key.decode("ascii"),
            },
        ]

        repository = self._get_repository_client()
        (result, created_deploykey, err_msg) = repository.deploykeys().create(
            app.config["REGISTRY_TITLE"] + " webhook key", public_key.decode("ascii")
        )

        if not result:
            msg = "Unable to add deploy key to repository: %s" % err_msg
            raise TriggerActivationException(msg)

        config["deploy_key_id"] = created_deploykey["pk"]

        # Add a webhook callback.
        description = "Webhook for invoking builds on %s" % app.config["REGISTRY_TITLE_SHORT"]
        webhook_events = ["repo:push"]
        (result, created_webhook, err_msg) = repository.webhooks().create(
            description, standard_webhook_url, webhook_events
        )

        if not result:
            msg = "Unable to add webhook to repository: %s" % err_msg
            raise TriggerActivationException(msg)

        config["webhook_id"] = created_webhook["uuid"]
        self.config = config
        return config, {"private_key": private_key.decode("ascii")}

    def deactivate(self):
        config = self.config

        webhook_id = config.pop("webhook_id", None)
        deploy_key_id = config.pop("deploy_key_id", None)
        repository = self._get_repository_client()

        # Remove the webhook.
        if webhook_id is not None:
            (result, _, err_msg) = repository.webhooks().delete(webhook_id)
            if not result:
                msg = "Unable to remove webhook from repository: %s" % err_msg
                raise TriggerDeactivationException(msg)

        # Remove the public key.
        if deploy_key_id is not None:
            (result, _, err_msg) = repository.deploykeys().delete(deploy_key_id)
            if not result:
                msg = "Unable to remove deploy key from repository: %s" % err_msg
                raise TriggerDeactivationException(msg)

        return config

    def list_build_source_namespaces(self):
        bitbucket_client = self._get_authorized_client()
        (result, data, err_msg) = bitbucket_client.get_visible_repositories()
        if not result:
            raise RepositoryReadException("Could not read repository list: " + err_msg)

        namespaces = {}
        for repo in data:
            owner = repo["owner"]

            if owner in namespaces:
                namespaces[owner]["score"] = namespaces[owner]["score"] + 1
            else:
                namespaces[owner] = {
                    "personal": owner == self.config.get("nickname", self.config.get("username")),
                    "id": owner,
                    "title": owner,
                    "avatar_url": repo["logo"],
                    "url": "https://bitbucket.org/%s" % (owner),
                    "score": 1,
                }

        return BuildTriggerHandler.build_namespaces_response(namespaces)

    def list_build_sources_for_namespace(self, namespace):
        def repo_view(repo):
            last_modified = dateutil.parser.parse(repo["utc_last_updated"])

            return {
                "name": repo["slug"],
                "full_name": "%s/%s" % (repo["owner"], repo["slug"]),
                "description": repo["description"] or "",
                "last_updated": timegm(last_modified.utctimetuple()),
                "url": "https://bitbucket.org/%s/%s" % (repo["owner"], repo["slug"]),
                "has_admin_permissions": repo["read_only"] is False,
                "private": repo["is_private"],
            }

        bitbucket_client = self._get_authorized_client()
        (result, data, err_msg) = bitbucket_client.get_visible_repositories()
        if not result:
            raise RepositoryReadException("Could not read repository list: " + err_msg)

        repos = [repo_view(repo) for repo in data if repo["owner"] == namespace]
        return BuildTriggerHandler.build_sources_response(repos)

    def list_build_subdirs(self):
        config = self.config
        repository = self._get_repository_client()

        # Find the first matching branch.
        repo_branches = self.list_field_values("branch_name") or []
        branches = find_matching_branches(config, repo_branches)
        if not branches:
            branches = [self._get_default_branch(repository)]

        (result, data, err_msg) = repository.get_path_contents("", revision=branches[0])
        if not result:
            raise RepositoryReadException(err_msg)

        files = set([f["path"] for f in data["files"]])
        return [
            "/" + file_path
            for file_path in files
            if self.filename_is_dockerfile(os.path.basename(file_path))
        ]

    def load_dockerfile_contents(self):
        repository = self._get_repository_client()
        path = self.get_dockerfile_path()

        (result, data, err_msg) = repository.get_raw_path_contents(path, revision="master")
        if not result:
            return None

        return data

    def list_field_values(self, field_name, limit=None):
        if "build_source" not in self.config:
            return None

        source = self.config["build_source"]
        (namespace, name) = source.split("/")

        bitbucket_client = self._get_authorized_client()
        repository = bitbucket_client.for_namespace(namespace).repositories().get(name)

        if field_name == "refs":
            (result, data, _) = repository.get_branches_and_tags()
            if not result:
                return None

            branches = [b["name"] for b in data["branches"]]
            tags = [t["name"] for t in data["tags"]]

            return [{"kind": "branch", "name": b} for b in branches] + [
                {"kind": "tag", "name": tag} for tag in tags
            ]

        if field_name == "tag_name":
            (result, data, _) = repository.get_tags()
            if not result:
                return None

            tags = list(data.keys())
            if limit:
                tags = tags[0:limit]

            return tags

        if field_name == "branch_name":
            (result, data, _) = repository.get_branches()
            if not result:
                return None

            branches = list(data.keys())
            if limit:
                branches = branches[0:limit]

            return branches

        return None

    def get_repository_url(self):
        source = self.config["build_source"]
        (namespace, name) = source.split("/")
        return "https://bitbucket.org/%s/%s" % (namespace, name)

    def handle_trigger_request(self, request):
        payload = request.get_json()
        if payload is None:
            raise InvalidPayloadException("Missing payload")

        logger.debug("Got BitBucket request: %s", payload)

        repository = self._get_repository_client()
        default_branch = self._get_default_branch(repository)

        metadata = get_transformed_webhook_payload(payload, default_branch=default_branch)
        prepared = self.prepare_build(metadata)

        # Check if we should skip this build.
        raise_if_skipped_build(prepared, self.config)
        return prepared

    def manual_start(self, run_parameters=None):
        run_parameters = run_parameters or {}
        repository = self._get_repository_client()
        bitbucket_client = self._get_authorized_client()

        def get_branch_sha(branch_name):
            # Lookup the commit SHA for the branch.
            (result, data, _) = repository.get_branch(branch_name)
            if not result:
                raise TriggerStartException("Could not find branch in repository")

            return data["target"]["hash"]

        def get_tag_sha(tag_name):
            # Lookup the commit SHA for the tag.
            (result, data, _) = repository.get_tag(tag_name)
            if not result:
                raise TriggerStartException("Could not find tag in repository")

            return data["target"]["hash"]

        def lookup_author(email_address):
            (result, data, _) = bitbucket_client.accounts().get_profile(email_address)
            return data if result else None

        # Find the branch or tag to build.
        default_branch = self._get_default_branch(repository)
        (commit_sha, ref) = determine_build_ref(
            run_parameters, get_branch_sha, get_tag_sha, default_branch
        )

        # Lookup the commit SHA in BitBucket.
        (result, commit_info, _) = repository.changesets().get(commit_sha)
        if not result:
            raise TriggerStartException("Could not lookup commit SHA")

        # Return a prepared build for the commit.
        repository_name = "%s/%s" % (repository.namespace, repository.repository_name)
        metadata = get_transformed_commit_info(
            commit_info, ref, default_branch, repository_name, lookup_author
        )

        return self.prepare_build(metadata, is_manual=True)
