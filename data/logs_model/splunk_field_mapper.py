"""
Field mapping utilities for converting Splunk search results to Quay Log objects.

This module provides the SplunkLogMapper class which transforms Splunk search
result rows into Quay's Log datatype, handling field mapping, type conversion,
and batch lookups for performance.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil import parser as dateutil_parser

from data import model
from data.logs_model.datatypes import Log

logger = logging.getLogger(__name__)


class SplunkLogMapper:
    """
    Maps Splunk search result fields to Quay Log datatype.

    Splunk stores logs with these fields (from splunk_logs_model.py log_action):
    - kind: str (e.g., "push_repo", "pull_repo")
    - account: str (namespace username)
    - performer: str (performer username)
    - repository: str (repository name)
    - ip: str (IP address)
    - metadata_json: dict (serialized JSON object)
    - datetime: str (ISO format timestamp)
    """

    def __init__(self):
        self._kind_map: Optional[Dict[str, int]] = None

    def map_logs(
        self,
        splunk_results: List[Dict[str, Any]],
        namespace_name: Optional[str] = None,
    ) -> List[Log]:
        """
        Convert a batch of Splunk results to Log objects.

        Uses batch lookups for users to avoid N+1 query problems.

        Args:
            splunk_results: List of Splunk result dictionaries
            namespace_name: Optional namespace name for context

        Returns:
            List of Log objects
        """
        _ = namespace_name  # Reserved for future use (e.g., repository lookups)

        if not splunk_results:
            return []

        usernames = set()
        for result in splunk_results:
            # Extract fields from _raw to get usernames
            fields = self._extract_log_fields(result)
            account = fields.get("account")
            performer = fields.get("performer")
            if account:
                usernames.add(account)
            if performer:
                usernames.add(performer)

        username_user_map = self._batch_lookup_users(list(usernames))

        logs = []
        for result in splunk_results:
            log = self._map_single_log(result, username_user_map)
            if log is not None:
                logs.append(log)

        return logs

    def _extract_log_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract log fields from Splunk result.

        Splunk stores the event data in _raw as a JSON string. This method
        parses _raw to extract the actual log fields, falling back to
        top-level fields if _raw is not available.

        Args:
            result: Splunk result dictionary

        Returns:
            Dictionary with extracted log fields
        """
        # Try to parse _raw field which contains the actual JSON event data
        raw_data = result.get("_raw")
        if raw_data and isinstance(raw_data, str):
            try:
                parsed = json.loads(raw_data)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse _raw field as JSON")

        # Fall back to top-level fields (for indexed field extraction)
        return result

    def _map_single_log(
        self,
        result: Dict[str, Any],
        username_user_map: Dict[str, Any],
    ) -> Optional[Log]:
        """
        Map a single Splunk result to a Log object.

        Args:
            result: Splunk result dictionary
            username_user_map: Pre-fetched username to user map

        Returns:
            Log object or None if mapping fails
        """
        try:
            # Extract fields from _raw JSON or fall back to top-level fields
            fields = self._extract_log_fields(result)

            kind_name = fields.get("kind")
            kind_id = self._get_kind_id(kind_name) if kind_name else 0

            account_username = fields.get("account")
            account_user = username_user_map.get(account_username) if account_username else None

            account_organization = None
            account_email = None
            account_robot = None
            if account_user:
                account_organization = getattr(account_user, "organization", None)
                account_email = getattr(account_user, "email", None)
                account_robot = getattr(account_user, "robot", None)

            performer_username = fields.get("performer")
            performer_user = (
                username_user_map.get(performer_username) if performer_username else None
            )

            performer_email = None
            performer_robot = None
            if performer_user:
                performer_email = getattr(performer_user, "email", None)
                performer_robot = getattr(performer_user, "robot", None)

            dt = self._parse_datetime(fields.get("datetime"))

            metadata = self._parse_metadata(fields.get("metadata_json"))
            metadata_json = json.dumps(metadata) if isinstance(metadata, dict) else "{}"

            ip = fields.get("ip")

            return Log(
                metadata_json=metadata_json,
                ip=ip,
                datetime=dt,
                performer_email=performer_email,
                performer_username=performer_username,
                performer_robot=performer_robot,
                account_organization=account_organization,
                account_username=account_username,
                account_email=account_email,
                account_robot=account_robot,
                kind_id=kind_id,
            )
        except Exception as e:
            logger.warning("Failed to map Splunk log result: %s", e)
            return None

    def _get_kind_id(self, kind_name: str) -> int:
        """
        Map kind name to kind_id using cached log entry kinds.

        Args:
            kind_name: The log entry kind name (e.g., "push_repo")

        Returns:
            The kind_id integer, or 0 if not found
        """
        if self._kind_map is None:
            self._kind_map = model.log.get_log_entry_kinds()

        kind_id = self._kind_map.get(kind_name)
        if kind_id is None:
            logger.warning("Unknown log entry kind: %s", kind_name)
            return 0
        return kind_id

    def _parse_datetime(self, datetime_value: Any) -> Optional[datetime]:
        """
        Parse Splunk datetime string to Python datetime.

        Handles various formats including ISO format and Splunk's default format.

        Args:
            datetime_value: Datetime as string or datetime object

        Returns:
            Python datetime object or None if parsing fails
        """
        if datetime_value is None:
            return None

        if isinstance(datetime_value, datetime):
            return datetime_value

        if isinstance(datetime_value, str):
            try:
                return dateutil_parser.parse(datetime_value)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to parse datetime '%s': %s", datetime_value, e)
                return None

        return None

    def _parse_metadata(self, metadata_value: Any) -> Dict[str, Any]:
        """
        Parse metadata field to dict, handling string or dict input.

        Args:
            metadata_value: Metadata as dict or JSON string

        Returns:
            Parsed dictionary or empty dict if parsing fails
        """
        if metadata_value is None:
            return {}

        if isinstance(metadata_value, dict):
            return metadata_value

        if isinstance(metadata_value, str):
            try:
                parsed = json.loads(metadata_value)
                if isinstance(parsed, dict):
                    return parsed
                return {}
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse metadata_json as JSON string")
                return {}

        return {}

    def _batch_lookup_users(self, usernames: List[str]) -> Dict[str, Any]:
        """
        Batch lookup users by username.

        Uses a single query with IN clause for efficiency.
        No cross-request caching — each call does a fresh lookup,
        similar to how the Elasticsearch model handles user lookups.

        Args:
            usernames: List of usernames to look up

        Returns:
            Dictionary mapping username to user object
        """
        if not usernames:
            return {}

        try:
            return model.user.get_namespace_users_by_usernames(usernames)
        except Exception:
            logger.exception("Failed to batch lookup users, falling back to None")
            return {username: None for username in usernames}
