"""
OpenShift federated users for Quay.

Extends OIDCUsers with OpenShift-specific functionality for group iteration
and background team synchronization.
"""

import logging
import os

import requests

import app
from data.users.externaloidc import OIDCUsers
from data.users.federated import UserInformation
from util.security.serviceaccount import (
    SERVICE_ACCOUNT_TOKEN_PATH,
    get_ssl_verification,
)

logger = logging.getLogger(__name__)


class OpenShiftUsers(OIDCUsers):
    """
    OpenShift-specific federated users with group iteration support.

    This class extends OIDCUsers to add background team sync capability
    by implementing iterate_group_members() using the OpenShift API.
    """

    def __init__(
        self,
        client_id,
        client_secret,
        oidc_server,
        service_name,
        login_scopes,
        preferred_group_claim_name,
        openshift_api_url=None,
        service_account_token_path=None,
        requires_email=False,  # OpenShift doesn't provide email by default
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            oidc_server=oidc_server,
            service_name=service_name,
            login_scopes=login_scopes,
            preferred_group_claim_name=preferred_group_claim_name,
            requires_email=requires_email,
        )
        # Override federated service to distinguish from generic OIDC
        self._federated_service = "openshift"
        self._openshift_api_url = openshift_api_url or self._auto_detect_api_url()
        self._sa_token_path = service_account_token_path or SERVICE_ACCOUNT_TOKEN_PATH

    def _auto_detect_api_url(self):
        """
        Auto-detect OpenShift API URL from in-cluster environment.
        """
        k8s_host = os.environ.get("KUBERNETES_SERVICE_HOST")
        k8s_port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        if k8s_host:
            return f"https://{k8s_host}:{k8s_port}"
        return None

    def _get_service_account_token(self):
        """
        Get the in-cluster service account token for API calls.
        """
        try:
            with open(self._sa_token_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Service account token not found at %s", self._sa_token_path)
            return None
        except Exception as e:
            logger.error("Failed to read service account token: %s", e)
            return None

    def service_metadata(self):
        """
        Return metadata about this auth service for display to superusers.
        """
        metadata = {"openshift_api_url": self._openshift_api_url}

        # Try to get cluster info
        if self._openshift_api_url:
            try:
                sa_token = self._get_service_account_token()
                if sa_token:
                    headers = {"Authorization": f"Bearer {sa_token}"}
                    response = requests.get(
                        f"{self._openshift_api_url}/version",
                        headers=headers,
                        timeout=5,
                        verify=get_ssl_verification(),
                    )
                    if response.status_code == 200:
                        version_info = response.json()
                        metadata["kubernetes_version"] = version_info.get("gitVersion")
            except Exception:
                pass

        return metadata

    def check_group_lookup_args(self, group_lookup_args, disable_pagination=False):
        """
        Verify that the specified group exists in OpenShift.

        Args:
            group_lookup_args: Dict with 'group_name' key

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        group_name = group_lookup_args.get("group_name")
        if not group_name:
            return (False, "Group name is required")

        if not self._openshift_api_url:
            return (False, "OpenShift API URL not configured")

        sa_token = self._get_service_account_token()
        if not sa_token:
            return (False, "Service account token not available")

        try:
            headers = {"Authorization": f"Bearer {sa_token}"}
            api_url = f"{self._openshift_api_url}/apis/user.openshift.io/v1/groups/{group_name}"
            response = requests.get(
                api_url, headers=headers, timeout=10, verify=get_ssl_verification()
            )

            if response.status_code == 200:
                return (True, None)
            elif response.status_code == 404:
                return (False, f"Group '{group_name}' not found in OpenShift")
            elif response.status_code == 403:
                return (False, "Insufficient permissions to access OpenShift groups")
            else:
                return (False, f"OpenShift API returned status {response.status_code}")

        except requests.exceptions.Timeout:
            return (False, "Timeout connecting to OpenShift API")
        except requests.exceptions.ConnectionError:
            return (False, "Could not connect to OpenShift API")
        except Exception as e:
            logger.exception("Error checking OpenShift group: %s", e)
            return (False, f"Error checking group: {str(e)}")

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        """
        Iterate over members of an OpenShift group.

        This is used by the background team sync worker to synchronize
        team membership with OpenShift groups.

        Args:
            group_lookup_args: Dict with 'group_name' key
            page_size: Ignored (OpenShift returns all members at once)
            disable_pagination: Ignored

        Returns:
            tuple: (iterator of (UserInformation, error), error_message)
        """
        group_name = group_lookup_args.get("group_name")
        if not group_name:
            return (None, "Group name is required")

        if not self._openshift_api_url:
            return (None, "OpenShift API URL not configured")

        sa_token = self._get_service_account_token()
        if not sa_token:
            return (None, "Service account token not available")

        try:
            headers = {"Authorization": f"Bearer {sa_token}"}
            group_url = f"{self._openshift_api_url}/apis/user.openshift.io/v1/groups/{group_name}"
            response = requests.get(
                group_url, headers=headers, timeout=10, verify=get_ssl_verification()
            )

            if response.status_code == 404:
                return (None, f"Group '{group_name}' not found")

            if response.status_code != 200:
                return (None, f"OpenShift API returned status {response.status_code}")

            group_data = response.json()
            usernames = group_data.get("users", [])

            def member_iterator():
                for username in usernames:
                    # Fetch user details from OpenShift
                    try:
                        user_url = (
                            f"{self._openshift_api_url}/apis/user.openshift.io/v1/users/{username}"
                        )
                        user_response = requests.get(
                            user_url, headers=headers, timeout=10, verify=get_ssl_verification()
                        )

                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            metadata = user_data.get("metadata", {})
                            yield (
                                UserInformation(
                                    username=metadata.get("name", username),
                                    email=None,  # OpenShift doesn't provide email
                                    id=metadata.get("uid", username),
                                ),
                                None,
                            )
                        else:
                            # User might have been deleted, skip
                            logger.warning(
                                "Could not fetch OpenShift user %s: status %s",
                                username,
                                user_response.status_code,
                            )
                            yield (None, f"Could not fetch user {username}")

                    except Exception as e:
                        logger.warning("Error fetching OpenShift user %s: %s", username, e)
                        yield (None, f"Error fetching user {username}: {str(e)}")

            return (member_iterator(), None)

        except requests.exceptions.Timeout:
            return (None, "Timeout connecting to OpenShift API")
        except requests.exceptions.ConnectionError:
            return (None, "Could not connect to OpenShift API")
        except Exception as e:
            logger.exception("Error iterating OpenShift group members: %s", e)
            return (None, f"Error iterating group members: {str(e)}")

    def get_user(self, username_or_email):
        """
        Look up a user in OpenShift by username.

        Note: OpenShift doesn't support email-based lookup.
        """
        if not self._openshift_api_url:
            return (None, "OpenShift API URL not configured")

        sa_token = self._get_service_account_token()
        if not sa_token:
            return (None, "Service account token not available")

        try:
            headers = {"Authorization": f"Bearer {sa_token}"}
            user_url = (
                f"{self._openshift_api_url}/apis/user.openshift.io/v1/users/{username_or_email}"
            )
            response = requests.get(
                user_url, headers=headers, timeout=10, verify=get_ssl_verification()
            )

            if response.status_code == 404:
                return (None, f"User '{username_or_email}' not found")

            if response.status_code != 200:
                return (None, f"OpenShift API returned status {response.status_code}")

            user_data = response.json()
            metadata = user_data.get("metadata", {})

            return (
                UserInformation(
                    username=metadata.get("name", username_or_email),
                    email=None,
                    id=metadata.get("uid", username_or_email),
                ),
                None,
            )

        except Exception as e:
            logger.exception("Error looking up OpenShift user: %s", e)
            return (None, f"Error looking up user: {str(e)}")

    def query_users(self, query, limit=20):
        """
        Search for users in OpenShift.

        OpenShift doesn't have a native user search API, so we list all users
        and filter locally. This may be slow for large clusters.
        """
        if not self._openshift_api_url:
            return ([], self._federated_service, "OpenShift API URL not configured")

        sa_token = self._get_service_account_token()
        if not sa_token:
            return ([], self._federated_service, "Service account token not available")

        try:
            headers = {"Authorization": f"Bearer {sa_token}"}
            users_url = f"{self._openshift_api_url}/apis/user.openshift.io/v1/users"
            response = requests.get(
                users_url, headers=headers, timeout=30, verify=get_ssl_verification()
            )

            if response.status_code != 200:
                return (
                    [],
                    self._federated_service,
                    f"OpenShift API returned status {response.status_code}",
                )

            users_data = response.json()
            items = users_data.get("items", [])

            # Filter users matching the query
            query_lower = query.lower()
            matching_users = []
            for user in items:
                username = user.get("metadata", {}).get("name", "")
                if query_lower in username.lower():
                    matching_users.append(
                        UserInformation(
                            username=username,
                            email=None,
                            id=user.get("metadata", {}).get("uid", username),
                        )
                    )
                    if len(matching_users) >= limit:
                        break

            return (matching_users, self._federated_service, None)

        except Exception as e:
            logger.exception("Error querying OpenShift users: %s", e)
            return ([], self._federated_service, f"Error querying users: {str(e)}")

    def is_superuser(self, username: str):
        """
        Check if user is a superuser.

        Delegates to config-based check.
        """
        return None

    def is_global_readonly_superuser(self, username: str):
        """
        Check if user is a global read-only superuser.

        Delegates to config-based check.
        """
        return None

    def is_restricted_user(self, username):
        """
        Check if user is restricted.

        Delegates to config-based check.
        """
        return None

    def ping(self):
        """
        Check connectivity to OpenShift API.
        """
        if not self._openshift_api_url:
            return (False, "OpenShift API URL not configured")

        sa_token = self._get_service_account_token()
        if not sa_token:
            return (False, "Service account token not available")

        try:
            headers = {"Authorization": f"Bearer {sa_token}"}
            response = requests.get(
                f"{self._openshift_api_url}/apis/user.openshift.io/v1",
                headers=headers,
                timeout=5,
                verify=get_ssl_verification(),
            )
            if response.status_code == 200:
                return (True, None)
            else:
                return (False, f"OpenShift API returned status {response.status_code}")
        except Exception as e:
            return (False, f"Could not connect to OpenShift API: {str(e)}")
