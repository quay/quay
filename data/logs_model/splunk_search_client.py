"""
Splunk Search Client for executing queries and retrieving audit log results.

This module provides the infrastructure for reading audit logs from Splunk,
complementing the existing write-only SplunkLogsProducer.
"""

import logging
import ssl
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from splunklib import client, results
from splunklib.binding import AuthenticationError  # type: ignore[import]

logger = logging.getLogger(__name__)


class SplunkSearchError(Exception):
    """Base exception for Splunk search errors."""

    pass


class SplunkSearchTimeoutError(SplunkSearchError):
    """Exception raised when a Splunk search exceeds the configured timeout."""

    pass


class SplunkConnectionError(SplunkSearchError):
    """Exception raised when connection to Splunk fails."""

    pass


class SplunkAuthenticationError(SplunkSearchError):
    """Exception raised when authentication to Splunk fails."""

    pass


@dataclass
class SplunkSearchResults:
    """Results from a Splunk search query."""

    results: List[Dict[str, Any]]
    total_count: int
    offset: int
    has_more: bool


class SplunkSearchClient:
    """
    Client for executing searches against Splunk and retrieving results.
    Uses splunklib SDK for search API operations.
    """

    def __init__(
        self,
        host: str,
        port: int,
        bearer_token: str,
        url_scheme: str = "https",
        verify_ssl: bool = True,
        ssl_ca_path: Optional[str] = None,
        index_prefix: Optional[str] = None,
        search_timeout: int = 60,
        max_results: int = 10000,
    ):
        """
        Initialize Splunk search client with connection parameters.

        Args:
            host: Splunk server hostname
            port: Splunk server port
            bearer_token: Bearer token for authentication
            url_scheme: URL scheme (http or https)
            verify_ssl: Whether to verify SSL certificates
            ssl_ca_path: Path to CA certificate file for SSL verification
            index_prefix: Splunk index name to search
            search_timeout: Maximum time in seconds to wait for search completion
            max_results: Maximum number of results to return per search
        """
        self._host = host
        self._port = port
        self._bearer_token = bearer_token
        self._url_scheme = url_scheme
        self._verify_ssl = verify_ssl
        self._ssl_ca_path = ssl_ca_path
        self._index_prefix = index_prefix
        self._search_timeout = search_timeout
        self._max_results = max_results
        self._service: Optional[client.Service] = None

    def _get_connection(self) -> client.Service:
        """
        Establish or return existing connection to Splunk.

        Returns:
            Splunk service client

        Raises:
            SplunkConnectionError: If connection fails
            SplunkAuthenticationError: If authentication fails
        """
        if self._service is not None:
            return self._service

        connect_args = {
            "host": self._host,
            "port": self._port,
            "token": self._bearer_token,
            "scheme": self._url_scheme,
            "verify": self._verify_ssl,
            "autologin": True,
        }

        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        if not self._verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        if self._ssl_ca_path:
            try:
                context.load_verify_locations(cafile=self._ssl_ca_path)
            except ssl.SSLError as e:
                raise SplunkConnectionError(f"SSL cert is not valid: {e}")
            except FileNotFoundError as e:
                raise SplunkConnectionError(f"Path to cert file is not valid: {e}")
        connect_args["context"] = context

        try:
            self._service = client.connect(**connect_args)
            return self._service
        except AuthenticationError as e:
            raise SplunkAuthenticationError(f"Authentication to Splunk failed: {e}")
        except ConnectionRefusedError as e:
            raise SplunkConnectionError(f"Connection to Splunk refused: {e}")
        except Exception as e:
            raise SplunkConnectionError(f"Failed to connect to Splunk: {e}")

    def search(
        self,
        query: str,
        earliest_time: Optional[str] = None,
        latest_time: Optional[str] = None,
        max_count: Optional[int] = None,
        offset: int = 0,
    ) -> SplunkSearchResults:
        """
        Execute a search query and return results.

        Args:
            query: SPL search query (should not include 'search' command prefix)
            earliest_time: Start time for search (Splunk time format)
            latest_time: End time for search (Splunk time format)
            max_count: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            SplunkSearchResults containing the query results

        Raises:
            SplunkSearchError: If search execution fails
            SplunkSearchTimeoutError: If search exceeds timeout
        """
        service = self._get_connection()

        spl_query = self._build_search_query(query)
        if max_count is None:
            max_count = self._max_results

        search_kwargs = {
            "exec_mode": "normal",
            "count": max_count,
            "offset": offset,
        }
        if earliest_time:
            search_kwargs["earliest_time"] = earliest_time
        if latest_time:
            search_kwargs["latest_time"] = latest_time

        try:
            job = service.jobs.create(spl_query, **search_kwargs)
            self._wait_for_job_completion(job, self._search_timeout)

            result_list = self._get_results_from_job(job, max_count, offset)

            total_count = int(job["resultCount"])
            has_more = (offset + len(result_list)) < total_count

            return SplunkSearchResults(
                results=result_list,
                total_count=total_count,
                offset=offset,
                has_more=has_more,
            )
        except SplunkSearchTimeoutError:
            raise
        except SplunkSearchError:
            raise
        except Exception as e:
            logger.exception("Error executing Splunk search: %s", e)
            raise SplunkSearchError(f"Search execution failed: {e}")

    def search_with_stats(
        self,
        query: str,
        earliest_time: Optional[str] = None,
        latest_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a search with stats/aggregation commands.

        This method is designed for queries that include transforming commands
        like stats, chart, timechart, etc.

        Args:
            query: SPL search query with aggregation commands
            earliest_time: Start time for search
            latest_time: End time for search

        Returns:
            List of result dictionaries from the aggregation

        Raises:
            SplunkSearchError: If search execution fails
            SplunkSearchTimeoutError: If search exceeds timeout
        """
        service = self._get_connection()

        spl_query = self._build_search_query(query)

        search_kwargs = {"exec_mode": "normal"}
        if earliest_time:
            search_kwargs["earliest_time"] = earliest_time
        if latest_time:
            search_kwargs["latest_time"] = latest_time

        try:
            job = service.jobs.create(spl_query, **search_kwargs)
            self._wait_for_job_completion(job, self._search_timeout)
            return self._get_results_from_job(job)
        except SplunkSearchTimeoutError:
            raise
        except SplunkSearchError:
            raise
        except Exception as e:
            logger.exception("Error executing Splunk stats search: %s", e)
            raise SplunkSearchError(f"Stats search execution failed: {e}")

    def count(
        self,
        query: str,
        earliest_time: Optional[str] = None,
        latest_time: Optional[str] = None,
        timeout: int = 30,
    ) -> int:
        """
        Execute a search and return only the count of matching events.

        Args:
            query: SPL search query
            earliest_time: Start time for search
            latest_time: End time for search
            timeout: Maximum wait time in seconds (default 30)

        Returns:
            Count of matching events

        Raises:
            SplunkSearchError: If search execution fails
            SplunkSearchTimeoutError: If search exceeds timeout
        """
        service = self._get_connection()

        count_query = self._build_search_query(query) + " | stats count"

        search_kwargs = {"exec_mode": "normal"}
        if earliest_time:
            search_kwargs["earliest_time"] = earliest_time
        if latest_time:
            search_kwargs["latest_time"] = latest_time

        try:
            job = service.jobs.create(count_query, **search_kwargs)
            self._wait_for_job_completion(job, timeout)

            result_list = self._get_results_from_job(job)
            if result_list and "count" in result_list[0]:
                return int(result_list[0]["count"])
            return 0
        except SplunkSearchTimeoutError:
            raise
        except SplunkSearchError:
            raise
        except Exception as e:
            logger.exception("Error executing Splunk count query: %s", e)
            raise SplunkSearchError(f"Count query failed: {e}")

    def _build_search_query(self, query: str) -> str:
        """
        Build a full SPL search query with index prefix.

        Args:
            query: User-provided query fragment

        Returns:
            Full SPL query string
        """
        if self._index_prefix:
            return f"search index={self._index_prefix} {query}"
        return f"search {query}"

    def _wait_for_job_completion(self, job, timeout: int) -> None:
        """
        Wait for a Splunk search job to complete, with timeout.

        Args:
            job: Splunk search job
            timeout: Maximum time in seconds to wait

        Raises:
            SplunkSearchTimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()

        while not job.is_done():
            time.sleep(0.5)
            job.refresh()
            if (time.time() - start_time) > timeout:
                try:
                    job.cancel()
                except Exception:
                    pass
                raise SplunkSearchTimeoutError(f"Search exceeded timeout of {timeout} seconds")

    def _get_results_from_job(
        self,
        job,
        max_count: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Extract results from a completed Splunk search job.

        Args:
            job: Splunk search job
            max_count: Maximum results to fetch
            offset: Result offset

        Returns:
            List of result dictionaries
        """
        result_args = {"output_mode": "json"}
        if max_count is not None:
            result_args["count"] = max_count  # type: ignore[assignment]
        if offset > 0:
            result_args["offset"] = offset  # type: ignore[assignment]

        result_list = []
        reader = results.JSONResultsReader(job.results(**result_args))
        for result in reader:
            if isinstance(result, dict):
                result_list.append(result)

        return result_list
