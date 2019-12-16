import logging
import sys

from collections import defaultdict
from enum import Enum

from data.registry_model import registry_model
from notifications import notification_batch
from util.secscan import PRIORITY_LEVELS
from util.secscan.api import APIRequestFailure
from util.morecollections import AttrDict, StreamingDiffTracker, IndexedStreamingDiffTracker


logger = logging.getLogger(__name__)


class ProcessNotificationPageResult(Enum):
    FINISHED_PAGE = "Finished Page"
    FINISHED_PROCESSING = "Finished Processing"
    FAILED = "Failed"


class SecurityNotificationHandler(object):
    """
    Class to process paginated notifications from the security scanner and issue Quay
    vulnerability_found notifications for all necessary tags. Callers should initialize, call
    process_notification_page_data for each page until it returns FINISHED_PROCESSING or FAILED and,
    if succeeded, then call send_notifications to send out the notifications queued.

    NOTE: This is legacy code and should be removed once we're fully moved to Clair V4.
    """

    def __init__(self, legacy_secscan_api, results_per_stream):
        self.tags_by_repository_map = defaultdict(set)
        self.repository_map = {}
        self.check_map = {}
        self.layer_ids = set()
        self.legacy_secscan_api = legacy_secscan_api

        self.stream_tracker = None
        self.results_per_stream = results_per_stream
        self.vulnerability_info = None

    def send_notifications(self):
        """
        Sends all queued up notifications.
        """
        if self.vulnerability_info is None:
            return

        new_vuln = self.vulnerability_info
        new_severity = PRIORITY_LEVELS.get(
            new_vuln.get("Severity", "Unknown"), {"index": sys.maxsize}
        )

        # For each of the tags found, issue a notification.
        with notification_batch() as spawn_notification:
            for repository_id, tags in self.tags_by_repository_map.items():
                event_data = {
                    "tags": list(tags),
                    "vulnerability": {
                        "id": new_vuln["Name"],
                        "description": new_vuln.get("Description", None),
                        "link": new_vuln.get("Link", None),
                        "priority": new_severity["title"],
                        "has_fix": "FixedIn" in new_vuln,
                    },
                }

                spawn_notification(
                    self.repository_map[repository_id], "vulnerability_found", event_data
                )

    def process_notification_page_data(self, notification_page_data):
        """
        Processes the given notification page data to spawn vulnerability notifications as
        necessary.

        Returns the status of the processing.
        """
        if not "New" in notification_page_data:
            return self._done()

        new_data = notification_page_data["New"]
        old_data = notification_page_data.get("Old", {})

        new_vuln = new_data["Vulnerability"]
        old_vuln = old_data.get("Vulnerability", {})

        self.vulnerability_info = new_vuln

        new_layer_ids = new_data.get("LayersIntroducingVulnerability", [])
        old_layer_ids = old_data.get("LayersIntroducingVulnerability", [])

        new_severity = PRIORITY_LEVELS.get(
            new_vuln.get("Severity", "Unknown"), {"index": sys.maxsize}
        )
        old_severity = PRIORITY_LEVELS.get(
            old_vuln.get("Severity", "Unknown"), {"index": sys.maxsize}
        )

        # Check if the severity of the vulnerability has increased. If so, then we report this
        # vulnerability for *all* layers, rather than a difference, as it is important for everyone.
        if new_severity["index"] < old_severity["index"]:
            # The vulnerability has had its severity increased. Report for *all* layers.
            all_layer_ids = set(new_layer_ids) | set(old_layer_ids)
            for layer_id in all_layer_ids:
                self._report(layer_id)

            if "NextPage" not in notification_page_data:
                return self._done()
            else:
                return ProcessNotificationPageResult.FINISHED_PAGE

        # Otherwise, only send the notification to new layers. To find only the new layers, we
        # need to do a streaming diff vs the old layer IDs stream.

        # Check for ordered data. If found, we use the indexed tracker, which is faster and
        # more memory efficient.
        is_indexed = False
        if (
            "OrderedLayersIntroducingVulnerability" in new_data
            or "OrderedLayersIntroducingVulnerability" in old_data
        ):

            def tuplize(stream):
                return [(entry["LayerName"], entry["Index"]) for entry in stream]

            new_layer_ids = tuplize(new_data.get("OrderedLayersIntroducingVulnerability", []))
            old_layer_ids = tuplize(old_data.get("OrderedLayersIntroducingVulnerability", []))
            is_indexed = True

        # If this is the first call, initialize the tracker.
        if self.stream_tracker is None:
            self.stream_tracker = (
                IndexedStreamingDiffTracker(self._report, self.results_per_stream)
                if is_indexed
                else StreamingDiffTracker(self._report, self.results_per_stream)
            )

        # Call to add the old and new layer ID streams to the tracker. The tracker itself will
        # call _report whenever it has determined a new layer has been found.
        self.stream_tracker.push_new(new_layer_ids)
        self.stream_tracker.push_old(old_layer_ids)

        # Check to see if there are any additional pages to process.
        if "NextPage" not in notification_page_data:
            return self._done()
        else:
            return ProcessNotificationPageResult.FINISHED_PAGE

    def _done(self):
        if self.stream_tracker is not None:
            # Mark the tracker as done, so that it finishes reporting any outstanding layers.
            self.stream_tracker.done()

        # Process all the layers.
        if self.vulnerability_info is not None:
            if not self._process_layers():
                return ProcessNotificationPageResult.FAILED

        return ProcessNotificationPageResult.FINISHED_PROCESSING

    def _report(self, new_layer_id):
        self.layer_ids.add(new_layer_id)

    def _chunk(self, pairs, chunk_size):
        start_index = 0
        while start_index < len(pairs):
            yield pairs[start_index:chunk_size]
            start_index += chunk_size

    def _process_layers(self):
        cve_id = self.vulnerability_info["Name"]

        # Builds the pairs of layer ID and storage uuid.
        pairs = [tuple(layer_id.split(".", 2)) for layer_id in self.layer_ids]

        # Find the matching tags.
        for current_pairs in self._chunk(pairs, 50):
            tags = list(registry_model.yield_tags_for_vulnerability_notification(current_pairs))
            for tag in tags:
                # Verify that the tag's *top layer* has the vulnerability.
                if not tag.layer_id in self.check_map:
                    logger.debug("Checking if layer %s is vulnerable to %s", tag.layer_id, cve_id)
                    try:
                        self.check_map[
                            tag.layer_id
                        ] = self.legacy_secscan_api.check_layer_vulnerable(tag.layer_id, cve_id)
                    except APIRequestFailure:
                        return False

                logger.debug(
                    "Result of layer %s is vulnerable to %s check: %s",
                    tag.layer_id,
                    cve_id,
                    self.check_map[tag.layer_id],
                )

                if self.check_map[tag.layer_id]:
                    # Add the vulnerable tag to the list.
                    self.tags_by_repository_map[tag.repository.id].add(tag.name)
                    self.repository_map[tag.repository.id] = tag.repository

        return True
