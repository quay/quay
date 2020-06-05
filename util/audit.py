import logging
import random

from collections import namedtuple
from urllib.parse import urlparse

from flask import request

from app import analytics, userevents, ip_resolver
from auth.auth_context import get_authenticated_context, get_authenticated_user
from data.logs_model import logs_model
from util.request import get_request_ip

from data.readreplica import ReadOnlyModeException

logger = logging.getLogger(__name__)

Repository = namedtuple("Repository", ["namespace_name", "name", "id", "is_free_namespace"])


def wrap_repository(repo_obj):
    return Repository(
        namespace_name=repo_obj.namespace_user.username,
        name=repo_obj.name,
        id=repo_obj.id,
        is_free_namespace=repo_obj.namespace_user.stripe_id is None,
    )


def track_and_log(event_name, repo_obj, analytics_name=None, analytics_sample=1, **kwargs):
    repo_name = repo_obj.name
    namespace_name = repo_obj.namespace_name
    metadata = {
        "repo": repo_name,
        "namespace": namespace_name,
        "user-agent": request.user_agent.string,
    }
    metadata.update(kwargs)

    is_free_namespace = False
    if hasattr(repo_obj, "is_free_namespace"):
        is_free_namespace = repo_obj.is_free_namespace

    # Add auth context metadata.
    analytics_id = "anonymous"
    auth_context = get_authenticated_context()
    if auth_context is not None:
        analytics_id, context_metadata = auth_context.analytics_id_and_public_metadata()
        metadata.update(context_metadata)

    # Publish the user event (if applicable)
    logger.debug("Checking publishing %s to the user events system", event_name)
    if auth_context and auth_context.has_nonrobot_user:
        logger.debug("Publishing %s to the user events system", event_name)
        user_event_data = {
            "action": event_name,
            "repository": repo_name,
            "namespace": namespace_name,
        }

        event = userevents.get_event(auth_context.authed_user.username)
        event.publish_event_data("docker-cli", user_event_data)

    # Save the action to mixpanel.
    if random.random() < analytics_sample:
        if analytics_name is None:
            analytics_name = event_name

        logger.debug("Logging the %s to analytics engine", analytics_name)

        request_parsed = urlparse(request.url_root)
        extra_params = {
            "repository": "%s/%s" % (namespace_name, repo_name),
            "user-agent": request.user_agent.string,
            "hostname": request_parsed.hostname,
        }

        analytics.track(analytics_id, analytics_name, extra_params)

    # Add the resolved information to the metadata.
    logger.debug("Resolving IP address %s", get_request_ip())
    resolved_ip = ip_resolver.resolve_ip(get_request_ip())
    if resolved_ip is not None:
        metadata["resolved_ip"] = resolved_ip._asdict()

    logger.debug("Resolved IP address %s", get_request_ip())

    # Log the action to the database.
    logger.debug("Logging the %s to logs system", event_name)
    try:
        logs_model.log_action(
            event_name,
            namespace_name,
            performer=get_authenticated_user(),
            ip=get_request_ip(),
            metadata=metadata,
            repository=repo_obj,
            is_free_namespace=is_free_namespace,
        )
        logger.debug("Track and log of %s complete", event_name)
    except ReadOnlyModeException:
        pass
