import logging
import os

from abc import ABCMeta, abstractmethod
from jsonschema import validate
from six import add_metaclass

from endpoints.building import PreparedBuild
from data import model
from buildtrigger.triggerutil import get_trigger_config, InvalidServiceException
from util.jsontemplate import apply_data_to_obj, JSONTemplateParseException

logger = logging.getLogger(__name__)


NAMESPACES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "personal": {
                "type": "boolean",
                "description": "True if the namespace is the user's personal namespace",
            },
            "score": {"type": "number", "description": "Score of the relevance of the namespace",},
            "avatar_url": {
                "type": ["string", "null"],
                "description": "URL of the avatar for this namespace",
            },
            "url": {"type": "string", "description": "URL of the website to view the namespace",},
            "id": {"type": "string", "description": "Trigger-internal ID of the namespace",},
            "title": {"type": "string", "description": "Human-readable title of the namespace",},
        },
        "required": ["personal", "score", "avatar_url", "id", "title"],
    },
}

BUILD_SOURCES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the repository, without its namespace",
            },
            "full_name": {
                "type": "string",
                "description": "The name of the repository, with its namespace",
            },
            "description": {
                "type": "string",
                "description": "The description of the repository. May be an empty string",
            },
            "last_updated": {
                "type": "number",
                "description": "The date/time when the repository was last updated, since epoch in UTC",
            },
            "url": {
                "type": "string",
                "description": "The URL at which to view the repository in the browser",
            },
            "has_admin_permissions": {
                "type": "boolean",
                "description": "True if the current user has admin permissions on the repository",
            },
            "private": {"type": "boolean", "description": "True if the repository is private",},
        },
        "required": [
            "name",
            "full_name",
            "description",
            "last_updated",
            "url",
            "has_admin_permissions",
            "private",
        ],
    },
}

METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "commit": {
            "type": "string",
            "description": "first 7 characters of the SHA-1 identifier for a git commit",
            "pattern": "^([A-Fa-f0-9]{7,})$",
        },
        "parsed_ref": {
            "type": "object",
            "description": "The parsed information about the ref, if any",
            "properties": {
                "branch": {"type": "string", "description": "The branch name",},
                "tag": {"type": "string", "description": "The tag name",},
                "remote": {"type": "string", "description": "The remote name",},
            },
        },
        "git_url": {"type": "string", "description": "The GIT url to use for the checkout",},
        "ref": {
            "type": "string",
            "description": "git reference for a git commit",
            "pattern": r"^refs\/(heads|tags|remotes)\/(.+)$",
        },
        "default_branch": {
            "type": "string",
            "description": "default branch of the git repository",
        },
        "commit_info": {
            "type": "object",
            "description": "metadata about a git commit",
            "properties": {
                "short_sha": {
                    "type": "string",
                    "description": "The short SHA for this git commit",
                },
                "url": {"type": "string", "description": "URL to view a git commit",},
                "message": {"type": "string", "description": "git commit message",},
                "date": {"type": "string", "description": "timestamp for a git commit"},
                "author": {
                    "type": "object",
                    "description": "metadata about the author of a git commit",
                    "properties": {
                        "username": {"type": "string", "description": "username of the author",},
                        "url": {
                            "type": "string",
                            "description": "URL to view the profile of the author",
                        },
                        "avatar_url": {
                            "type": "string",
                            "description": "URL to view the avatar of the author",
                        },
                    },
                    "required": ["username"],
                },
                "committer": {
                    "type": "object",
                    "description": "metadata about the committer of a git commit",
                    "properties": {
                        "username": {"type": "string", "description": "username of the committer",},
                        "url": {
                            "type": "string",
                            "description": "URL to view the profile of the committer",
                        },
                        "avatar_url": {
                            "type": "string",
                            "description": "URL to view the avatar of the committer",
                        },
                    },
                    "required": ["username"],
                },
            },
            "required": ["message"],
        },
    },
    "required": ["commit", "git_url"],
}


@add_metaclass(ABCMeta)
class BuildTriggerHandler(object):
    def __init__(self, trigger, override_config=None):
        self.trigger = trigger
        self.config = override_config or get_trigger_config(trigger)

    @property
    def auth_token(self):
        """
        Returns the auth token for the trigger.
        """
        # NOTE: This check is for testing.
        if hasattr(self.trigger, "auth_token"):
            return self.trigger.auth_token

        if self.trigger.secure_auth_token is not None:
            return self.trigger.secure_auth_token.decrypt()

        return None

    @abstractmethod
    def load_dockerfile_contents(self):
        """
        Loads the Dockerfile found for the trigger's config and returns them or None if none could
        be found/loaded.
        """
        pass

    @abstractmethod
    def list_build_source_namespaces(self):
        """
        Take the auth information for the specific trigger type and load the list of namespaces that
        can contain build sources.
        """
        pass

    @abstractmethod
    def list_build_sources_for_namespace(self, namespace):
        """
        Take the auth information for the specific trigger type and load the list of repositories
        under the given namespace.
        """
        pass

    @abstractmethod
    def list_build_subdirs(self):
        """
        Take the auth information and the specified config so far and list all of the possible
        subdirs containing dockerfiles.
        """
        pass

    @abstractmethod
    def handle_trigger_request(self, request):
        """
        Transform the incoming request data into a set of actions.

        Returns a PreparedBuild.
        """
        pass

    @abstractmethod
    def is_active(self):
        """
        Returns True if the current build trigger is active.

        Inactive means further setup is needed.
        """
        pass

    @abstractmethod
    def activate(self, standard_webhook_url):
        """
        Activates the trigger for the service, with the given new configuration.

        Returns new public and private config that should be stored if successful.
        """
        pass

    @abstractmethod
    def deactivate(self):
        """
        Deactivates the trigger for the service, removing any hooks installed in the remote service.

        Returns the new config that should be stored if this trigger is going to be re-activated.
        """
        pass

    @abstractmethod
    def manual_start(self, run_parameters=None):
        """
        Manually creates a repository build for this trigger.

        Returns a PreparedBuild.
        """
        pass

    @abstractmethod
    def list_field_values(self, field_name, limit=None):
        """
        Lists all values for the given custom trigger field.

        For example, a trigger might have a field named "branches", and this method would return all
        branches.
        """
        pass

    @abstractmethod
    def get_repository_url(self):
        """
        Returns the URL of the current trigger's repository.

        Note that this operation can be called in a loop, so it should be as fast as possible.
        """
        pass

    @classmethod
    def filename_is_dockerfile(cls, file_name):
        """
        Returns whether the file is named Dockerfile or follows the convention <name>.Dockerfile.
        """
        return file_name.endswith(".Dockerfile") or "Dockerfile" == file_name

    @classmethod
    def service_name(cls):
        """
        Particular service implemented by subclasses.
        """
        raise NotImplementedError

    @classmethod
    def get_handler(cls, trigger, override_config=None):
        for subc in cls.__subclasses__():
            if subc.service_name() == trigger.service.name:
                return subc(trigger, override_config)

        raise InvalidServiceException("Unable to find service: %s" % trigger.service.name)

    def put_config_key(self, key, value):
        """
        Updates a config key in the trigger, saving it to the DB.
        """
        self.config[key] = value
        model.build.update_build_trigger(self.trigger, self.config)

    def set_auth_token(self, auth_token):
        """
        Sets the auth token for the trigger, saving it to the DB.
        """
        model.build.update_build_trigger(self.trigger, self.config, auth_token=auth_token)

    def get_dockerfile_path(self):
        """
        Returns the normalized path to the Dockerfile found in the subdirectory in the config.
        """
        dockerfile_path = self.config.get("dockerfile_path") or "Dockerfile"
        if dockerfile_path[0] == "/":
            dockerfile_path = dockerfile_path[1:]
        return dockerfile_path

    def prepare_build(self, metadata, is_manual=False):
        # Ensure that the metadata meets the scheme.
        validate(metadata, METADATA_SCHEMA)

        config = self.config
        commit_sha = metadata["commit"]

        # Create the prepared build.
        prepared = PreparedBuild(self.trigger)
        prepared.name_from_sha(commit_sha)

        prepared.subdirectory = config.get("dockerfile_path", None)
        prepared.context = config.get("context", None)
        prepared.is_manual = is_manual
        prepared.metadata = metadata
        prepared.tags = BuildTriggerHandler._determine_tags(config, metadata)
        return prepared

    @classmethod
    def _add_tag_from_ref(cls, tags, ref):
        if not ref:
            return

        branch = ref.split("/", 2)[-1]
        tags.add(branch)

    @classmethod
    def _add_latest_tag_if_default(cls, tags, ref, default_branch=None):
        if not ref:
            return

        branch = ref.split("/", 2)[-1]
        if default_branch is not None and branch == default_branch:
            tags.add("latest")

    @classmethod
    def _determine_tags(cls, config, metadata):
        tags = set()

        ref = metadata.get("ref", None)
        commit_sha = metadata["commit"]
        default_branch = metadata.get("default_branch", None)

        # Handle tagging. If there are defined tagging templates, use them.
        tag_templates = config.get("tag_templates")
        if tag_templates:
            updated_metadata = dict(metadata)
            updated_metadata["commit_info"] = updated_metadata.get("commit_info", {})
            updated_metadata["commit_info"]["short_sha"] = commit_sha[:7]

            if ref:
                _, kind, name = ref.split("/", 2)

                updated_metadata["parsed_ref"] = {}
                if kind == "heads":
                    updated_metadata["parsed_ref"]["branch"] = name
                elif kind == "tags":
                    updated_metadata["parsed_ref"]["tag"] = name
                elif kind == "remotes":
                    updated_metadata["parsed_ref"]["remote"] = name

            for tag_template in tag_templates:
                try:
                    result = apply_data_to_obj(tag_template, updated_metadata, missing="$MISSING$")
                    if result and "$MISSING$" in result:
                        result = None
                except JSONTemplateParseException:
                    logger.exception("Got except when parsing tag template `%s`", tag_template)
                    continue

                if result:
                    tags.add(result)

        # If allowed, tag from the ref.
        if ref is not None:
            if config.get("default_tag_from_ref", True):
                cls._add_tag_from_ref(tags, ref)

            if config.get("latest_for_default_branch", True):
                cls._add_latest_tag_if_default(tags, ref, default_branch)

        if not tags:
            tags = {commit_sha[:7]}

        return tags

    @classmethod
    def build_sources_response(cls, sources):
        validate(sources, BUILD_SOURCES_SCHEMA)
        return sources

    @classmethod
    def build_namespaces_response(cls, namespaces_dict):
        namespaces = list(namespaces_dict.values())
        validate(namespaces, NAMESPACES_SCHEMA)
        return namespaces

    @classmethod
    def get_parent_directory_mappings(cls, dockerfile_path, current_paths=None):
        """
        Returns a map of dockerfile_paths to it's possible contexts.
        """
        if dockerfile_path == "":
            return {}

        if dockerfile_path[0] != os.path.sep:
            dockerfile_path = os.path.sep + dockerfile_path

        dockerfile_path = os.path.normpath(dockerfile_path)
        all_paths = set()
        path, _ = os.path.split(dockerfile_path)
        if path == "":
            path = os.path.sep

        all_paths.add(path)
        for i in range(1, len(path.split(os.path.sep))):
            path, _ = os.path.split(path)
            all_paths.add(path)

        if current_paths:
            return dict({dockerfile_path: list(all_paths)}, **current_paths)

        return {dockerfile_path: list(all_paths)}
