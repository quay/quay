import json
import io
import logging
import re


class TriggerException(Exception):
    pass


class TriggerAuthException(TriggerException):
    pass


class InvalidPayloadException(TriggerException):
    pass


class BuildArchiveException(TriggerException):
    pass


class InvalidServiceException(TriggerException):
    pass


class TriggerActivationException(TriggerException):
    pass


class TriggerDeactivationException(TriggerException):
    pass


class TriggerStartException(TriggerException):
    pass


class ValidationRequestException(TriggerException):
    pass


class SkipRequestException(TriggerException):
    pass


class EmptyRepositoryException(TriggerException):
    pass


class RepositoryReadException(TriggerException):
    pass


class TriggerProviderException(TriggerException):
    pass


logger = logging.getLogger(__name__)


def determine_build_ref(run_parameters, get_branch_sha, get_tag_sha, default_branch):
    run_parameters = run_parameters or {}

    kind = ""
    value = ""

    if "refs" in run_parameters and run_parameters["refs"]:
        kind = run_parameters["refs"]["kind"]
        value = run_parameters["refs"]["name"]
    elif "branch_name" in run_parameters:
        kind = "branch"
        value = run_parameters["branch_name"]

    kind = kind or "branch"
    value = value or default_branch or "master"

    ref = "refs/tags/" + value if kind == "tag" else "refs/heads/" + value
    commit_sha = get_tag_sha(value) if kind == "tag" else get_branch_sha(value)
    return (commit_sha, ref)


def find_matching_branches(config, branches):
    if "branchtag_regex" in config:
        try:
            regex = re.compile(config["branchtag_regex"])
            return [branch for branch in branches if matches_ref("refs/heads/" + branch, regex)]
        except:
            pass

    return branches


def should_skip_commit(metadata):
    if "commit_info" in metadata:
        message = metadata["commit_info"]["message"]
        return "[skip build]" in message or "[build skip]" in message
    return False


def raise_if_skipped_build(prepared_build, config):
    """
    Raises a SkipRequestException if the given build should be skipped.
    """
    # Check to ensure we have metadata.
    if not prepared_build.metadata:
        logger.debug("Skipping request due to missing metadata for prepared build")
        raise SkipRequestException()

    # Check the branchtag regex.
    if "branchtag_regex" in config:
        try:
            regex = re.compile(config["branchtag_regex"])
        except:
            regex = re.compile(".*")

        if not matches_ref(prepared_build.metadata.get("ref"), regex):
            raise SkipRequestException()

    # Check the commit message.
    if should_skip_commit(prepared_build.metadata):
        logger.debug("Skipping request due to commit message request")
        raise SkipRequestException()


def matches_ref(ref, regex):
    match_string = ref.split("/", 1)[1]
    if not regex:
        return False

    m = regex.match(match_string)
    if not m:
        return False

    return len(m.group(0)) == len(match_string)


def raise_unsupported():
    raise io.UnsupportedOperation


def get_trigger_config(trigger):
    try:
        return json.loads(trigger.config)
    except ValueError:
        return {}
