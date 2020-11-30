import logging
import json

from jsonschema import validate, ValidationError
from buildtrigger.triggerutil import (
    RepositoryReadException,
    TriggerActivationException,
    TriggerStartException,
    ValidationRequestException,
    InvalidPayloadException,
    SkipRequestException,
    raise_if_skipped_build,
    find_matching_branches,
)

from buildtrigger.basehandler import BuildTriggerHandler

from buildtrigger.bitbuckethandler import (
    BITBUCKET_WEBHOOK_PAYLOAD_SCHEMA as bb_schema,
    get_transformed_webhook_payload as bb_payload,
)

from buildtrigger.githubhandler import (
    GITHUB_WEBHOOK_PAYLOAD_SCHEMA as gh_schema,
    get_transformed_webhook_payload as gh_payload,
)

from buildtrigger.gitlabhandler import (
    GITLAB_WEBHOOK_PAYLOAD_SCHEMA as gl_schema,
    get_transformed_webhook_payload as gl_payload,
)

from util.security.ssh import generate_ssh_keypair


logger = logging.getLogger(__name__)

# Defines an ordered set of tuples of the schemas and associated transformation functions
# for incoming webhook payloads.
SCHEMA_AND_HANDLERS = [
    (gh_schema, gh_payload),
    (bb_schema, bb_payload),
    (gl_schema, gl_payload),
]


def custom_trigger_payload(metadata, git_url):
    # First try the customhandler schema. If it matches, nothing more to do.
    custom_handler_validation_error = None
    try:
        validate(metadata, CustomBuildTrigger.payload_schema)
    except ValidationError as vex:
        custom_handler_validation_error = vex

    # Otherwise, try the defined schemas, in order, until we find a match.
    for schema, handler in SCHEMA_AND_HANDLERS:
        try:
            validate(metadata, schema)
        except ValidationError:
            continue

        result = handler(metadata)
        result["git_url"] = git_url
        return result

    # If we have reached this point and no other schemas validated, then raise the error for the
    # custom schema.
    if custom_handler_validation_error is not None:
        raise InvalidPayloadException(custom_handler_validation_error.message)

    metadata["git_url"] = git_url
    return metadata


class CustomBuildTrigger(BuildTriggerHandler):
    payload_schema = {
        "type": "object",
        "properties": {
            "commit": {
                "type": "string",
                "description": "first 7 characters of the SHA-1 identifier for a git commit",
                "pattern": "^([A-Fa-f0-9]{7,})$",
            },
            "ref": {
                "type": "string",
                "description": "git reference for a git commit",
                "pattern": "^refs\/(heads|tags|remotes)\/(.+)$",
            },
            "default_branch": {
                "type": "string",
                "description": "default branch of the git repository",
            },
            "commit_info": {
                "type": "object",
                "description": "metadata about a git commit",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to view a git commit",
                    },
                    "message": {
                        "type": "string",
                        "description": "git commit message",
                    },
                    "date": {"type": "string", "description": "timestamp for a git commit"},
                    "author": {
                        "type": "object",
                        "description": "metadata about the author of a git commit",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "username of the author",
                            },
                            "url": {
                                "type": "string",
                                "description": "URL to view the profile of the author",
                            },
                            "avatar_url": {
                                "type": "string",
                                "description": "URL to view the avatar of the author",
                            },
                        },
                        "required": ["username", "url", "avatar_url"],
                    },
                    "committer": {
                        "type": "object",
                        "description": "metadata about the committer of a git commit",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "username of the committer",
                            },
                            "url": {
                                "type": "string",
                                "description": "URL to view the profile of the committer",
                            },
                            "avatar_url": {
                                "type": "string",
                                "description": "URL to view the avatar of the committer",
                            },
                        },
                        "required": ["username", "url", "avatar_url"],
                    },
                },
                "required": ["url", "message", "date"],
            },
        },
        "required": ["commit", "ref", "default_branch"],
    }

    @classmethod
    def service_name(cls):
        return "custom-git"

    def is_active(self):
        return "credentials" in self.config

    def _metadata_from_payload(self, payload, git_url):
        # Parse the JSON payload.
        try:
            metadata = json.loads(payload)
        except ValueError as vex:
            raise InvalidPayloadException(vex.message)

        return custom_trigger_payload(metadata, git_url)

    def handle_trigger_request(self, request):
        payload = request.data
        if not payload:
            raise InvalidPayloadException("Missing expected payload")

        logger.debug("Payload %s", payload)

        metadata = self._metadata_from_payload(payload, self.config["build_source"])
        prepared = self.prepare_build(metadata)

        # Check if we should skip this build.
        raise_if_skipped_build(prepared, self.config)

        return prepared

    def manual_start(self, run_parameters=None):
        # commit_sha is the only required parameter
        commit_sha = run_parameters.get("commit_sha")
        if commit_sha is None:
            raise TriggerStartException("missing required parameter")

        config = self.config
        metadata = {
            "commit": commit_sha,
            "git_url": config["build_source"],
        }

        try:
            return self.prepare_build(metadata, is_manual=True)
        except ValidationError as ve:
            raise TriggerStartException(ve.message)

    def activate(self, standard_webhook_url):
        config = self.config
        public_key, private_key = generate_ssh_keypair()
        config["credentials"] = [
            {
                "name": "SSH Public Key",
                "value": public_key.decode("ascii"),
            },
            {
                "name": "Webhook Endpoint URL",
                "value": standard_webhook_url,
            },
        ]
        self.config = config
        return config, {"private_key": private_key.decode("ascii")}

    def deactivate(self):
        config = self.config
        config.pop("credentials", None)
        self.config = config
        return config

    def get_repository_url(self):
        return None

    def list_build_source_namespaces(self):
        raise NotImplementedError

    def list_build_sources_for_namespace(self, namespace):
        raise NotImplementedError

    def list_build_subdirs(self):
        raise NotImplementedError

    def list_field_values(self, field_name, limit=None):
        raise NotImplementedError

    def load_dockerfile_contents(self):
        raise NotImplementedError
