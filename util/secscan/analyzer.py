import logging
import logging.config

from collections import defaultdict

import features

from data.database import ExternalNotificationEvent, IMAGE_NOT_SCANNED_ENGINE_VERSION, Image
from data.model.tag import filter_tags_have_repository_event, get_tags_for_image
from data.model.image import set_secscan_status, get_image_with_storage_and_parent_base
from notifications import spawn_notification
from util.secscan import PRIORITY_LEVELS
from util.secscan.api import (
    APIRequestFailure,
    AnalyzeLayerException,
    MissingParentLayerException,
    InvalidLayerException,
    AnalyzeLayerRetryException,
)
from util.morecollections import AttrDict


logger = logging.getLogger(__name__)


class PreemptedException(Exception):
    """ Exception raised if another worker analyzed the image before this worker was able to do so.
  """


class LayerAnalyzer(object):
    """ Helper class to perform analysis of a layer via the security scanner. """

    def __init__(self, config, api):
        self._api = api
        self._target_version = config.get("SECURITY_SCANNER_ENGINE_VERSION_TARGET", 2)

    def analyze_recursively(self, layer):
        """ Analyzes a layer and all its parents. Raises a PreemptedException if the analysis was
        preempted by another worker.
    """
        try:
            self._analyze_recursively_and_check(layer)
        except MissingParentLayerException:
            # The parent layer of this layer was missing. Force a reanalyze.
            try:
                self._analyze_recursively_and_check(layer, force_parents=True)
            except MissingParentLayerException:
                # Parent is still missing... mark the layer as invalid.
                if not set_secscan_status(layer, False, self._target_version):
                    raise PreemptedException

    def _analyze_recursively_and_check(self, layer, force_parents=False):
        """ Analyzes a layer and all its parents, optionally forcing parents to be reanalyzed,
        and checking for various exceptions that can occur during analysis.
    """
        try:
            self._analyze_recursively(layer, force_parents=force_parents)
        except InvalidLayerException:
            # One of the parent layers is invalid, so this layer is invalid as well.
            if not set_secscan_status(layer, False, self._target_version):
                raise PreemptedException
        except AnalyzeLayerRetryException:
            # Something went wrong when trying to analyze the layer, but we should retry, so leave
            # the layer unindexed. Another worker will come along and handle it.
            raise APIRequestFailure
        except MissingParentLayerException:
            # Pass upward, as missing parent is handled in the analyze_recursively method.
            raise
        except AnalyzeLayerException:
            # Something went wrong when trying to analyze the layer and we cannot retry, so mark the
            # layer as invalid.
            logger.exception(
                "Got exception when trying to analyze layer %s via security scanner", layer.id
            )
            if not set_secscan_status(layer, False, self._target_version):
                raise PreemptedException

    def _analyze_recursively(self, layer, force_parents=False):
        # Check if there is a parent layer that needs to be analyzed.
        if layer.parent_id and (
            force_parents or layer.parent.security_indexed_engine < self._target_version
        ):
            try:
                base_query = get_image_with_storage_and_parent_base()
                parent_layer = base_query.where(Image.id == layer.parent_id).get()
            except Image.DoesNotExist:
                logger.warning(
                    "Image %s has Image %s as parent but doesn't exist.", layer.id, layer.parent_id
                )
                raise AnalyzeLayerException("Parent image not found")

            self._analyze_recursively(parent_layer, force_parents=force_parents)

        # Analyze the layer itself.
        self._analyze(layer, force_parents=force_parents)

    def _analyze(self, layer, force_parents=False):
        """ Analyzes a single layer.

        Return a tuple of two bools:
          - The first one tells us if we should evaluate its children.
          - The second one is set to False when another worker pre-empted the candidate's analysis
            for us.
    """
        # If the parent couldn't be analyzed with the target version or higher, we can't analyze
        # this image. Mark it as failed with the current target version.
        if not force_parents and (
            layer.parent_id
            and not layer.parent.security_indexed
            and layer.parent.security_indexed_engine >= self._target_version
        ):
            if not set_secscan_status(layer, False, self._target_version):
                raise PreemptedException

            # Nothing more to do.
            return

        # Make sure the image's storage is not marked as uploading. If so, nothing more to do.
        if layer.storage.uploading:
            if not set_secscan_status(layer, False, self._target_version):
                raise PreemptedException

            # Nothing more to do.
            return

        # Analyze the image.
        previously_security_indexed_successfully = layer.security_indexed
        previous_security_indexed_engine = layer.security_indexed_engine

        logger.info("Analyzing layer %s", layer.docker_image_id)
        analyzed_version = self._api.analyze_layer(layer)

        logger.info(
            "Analyzed layer %s successfully with version %s",
            layer.docker_image_id,
            analyzed_version,
        )

        # Mark the image as analyzed.
        if not set_secscan_status(layer, True, analyzed_version):
            # If the image was previously successfully marked as resolved, then set_secscan_status
            # might return False because we're not changing it (since this is a fixup).
            if not previously_security_indexed_successfully:
                raise PreemptedException

        # If we are the one who've done the job successfully first, then we need to decide if we should
        # send notifications. Notifications are sent if:
        #  1) This is a new layer
        #  2) This is an existing layer that previously did not index properly
        # We don't always send notifications as if we are re-indexing a successful layer for a newer
        # feature set in the security scanner, notifications will be spammy.
        is_new_image = previous_security_indexed_engine == IMAGE_NOT_SCANNED_ENGINE_VERSION
        is_existing_image_unindexed = (
            not is_new_image and not previously_security_indexed_successfully
        )
        if features.SECURITY_NOTIFICATIONS and (is_new_image or is_existing_image_unindexed):
            # Get the tags of the layer we analyzed.
            repository_map = defaultdict(list)
            event = ExternalNotificationEvent.get(name="vulnerability_found")
            matching = list(filter_tags_have_repository_event(get_tags_for_image(layer.id), event))

            for tag in matching:
                repository_map[tag.repository_id].append(tag)

            # If there is at least one tag,
            # Lookup the vulnerabilities for the image, now that it is analyzed.
            if len(repository_map) > 0:
                logger.debug("Loading data for layer %s", layer.id)
                try:
                    layer_data = self._api.get_layer_data(layer, include_vulnerabilities=True)
                except APIRequestFailure:
                    raise

                if layer_data is not None:
                    # Dispatch events for any detected vulnerabilities
                    logger.debug("Got data for layer %s: %s", layer.id, layer_data)
                    found_features = layer_data["Layer"].get("Features", [])
                    for repository_id in repository_map:
                        tags = repository_map[repository_id]
                        vulnerabilities = dict()

                        # Collect all the vulnerabilities found for the layer under each repository and send
                        # as a batch notification.
                        for feature in found_features:
                            if "Vulnerabilities" not in feature:
                                continue

                            for vulnerability in feature.get("Vulnerabilities", []):
                                vuln_data = {
                                    "id": vulnerability["Name"],
                                    "description": vulnerability.get("Description", None),
                                    "link": vulnerability.get("Link", None),
                                    "has_fix": "FixedBy" in vulnerability,
                                    # TODO: Change this key name if/when we change the event format.
                                    "priority": vulnerability.get("Severity", "Unknown"),
                                }

                                vulnerabilities[vulnerability["Name"]] = vuln_data

                        # TODO: remove when more endpoints have been converted to using
                        # interfaces
                        repository = AttrDict(
                            {
                                "namespace_name": tags[0].repository.namespace_user.username,
                                "name": tags[0].repository.name,
                            }
                        )

                        repo_vulnerabilities = list(vulnerabilities.values())
                        if not repo_vulnerabilities:
                            continue

                        priority_key = lambda v: PRIORITY_LEVELS.get(v["priority"], {}).get(
                            "index", 100
                        )
                        repo_vulnerabilities.sort(key=priority_key)

                        event_data = {
                            "tags": [tag.name for tag in tags],
                            "vulnerabilities": repo_vulnerabilities,
                            "vulnerability": repo_vulnerabilities[
                                0
                            ],  # For back-compat with existing events.
                        }

                        spawn_notification(repository, "vulnerability_found", event_data)
