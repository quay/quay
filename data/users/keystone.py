import logging
import os

from keystoneauth1.identity import v2 as keystone_v2_auth
from keystoneauth1.identity import v3 as keystone_v3_auth
from keystoneauth1 import session
from keystoneauth1.exceptions import ClientException
from keystoneclient.v2_0 import client as client_v2
from keystoneclient.v3 import client as client_v3
from keystoneclient.exceptions import AuthorizationFailure as KeystoneAuthorizationFailure
from keystoneclient.exceptions import Unauthorized as KeystoneUnauthorized
from keystoneclient.exceptions import NotFound as KeystoneNotFound
from data.users.federated import FederatedUsers, UserInformation
from util.itertoolrecipes import take

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10  # seconds


def get_keystone_users(
    auth_version,
    auth_url,
    admin_username,
    admin_password,
    admin_tenant,
    timeout=None,
    requires_email=True,
):
    if auth_version == 3:
        return KeystoneV3Users(
            auth_url, admin_username, admin_password, admin_tenant, timeout, requires_email
        )
    else:
        return KeystoneV2Users(
            auth_url, admin_username, admin_password, admin_tenant, timeout, requires_email
        )


class KeystoneV2Users(FederatedUsers):
    """
    Delegates authentication to OpenStack Keystone V2.
    """

    def __init__(
        self,
        auth_url,
        admin_username,
        admin_password,
        admin_tenant,
        timeout=None,
        requires_email=True,
    ):
        super(KeystoneV2Users, self).__init__("keystone", requires_email)
        self.auth_url = auth_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_tenant = admin_tenant
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.debug = os.environ.get("USERS_DEBUG") == "1"
        self.requires_email = requires_email

    def _get_client(self, username, password, tenant_name=None):
        if tenant_name:
            auth = keystone_v2_auth.Password(
                auth_url=self.auth_url,
                username=username,
                password=password,
                tenant_name=tenant_name,
            )
        else:
            auth = keystone_v2_auth.Password(
                auth_url=self.auth_url, username=username, password=password
            )

        sess = session.Session(auth=auth)
        client = client_v2.Client(session=sess, timeout=self.timeout, debug=self.debug)
        return client, sess

    def ping(self):
        try:
            _, sess = self._get_client(self.admin_username, self.admin_password, self.admin_tenant)
            assert sess.get_user_id()  # Make sure we loaded a valid user.
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized admin")
            return (False, "Keystone admin credentials are invalid: %s" % str(kut))
        except ClientException as e:
            logger.exception("Keystone unauthorized admin")
            return (False, "Keystone ping check failed: %s" % str(e))

        return (True, None)

    def at_least_one_user_exists(self):
        logger.debug("Checking if any users exist in Keystone")
        try:
            keystone_client, _ = self._get_client(
                self.admin_username, self.admin_password, self.admin_tenant
            )
            user_list = keystone_client.users.list(tenant_id=self.admin_tenant, limit=1)

            if len(user_list) < 1:
                return (False, None)

            return (True, None)
        except ClientException as e:
            # Catch exceptions to give the user our custom error message
            logger.exception("Unable to list users in Keystone")
            return (False, str(e))

    def verify_credentials(self, username_or_email, password):
        try:
            _, sess = self._get_client(username_or_email, password)
            user_id = sess.get_user_id()
        except KeystoneAuthorizationFailure as kaf:
            logger.exception("Keystone auth failure for user: %s", username_or_email)
            return (None, "Invalid username or password")
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized for user: %s", username_or_email)
            return (None, "Invalid username or password")
        except ClientException as ex:
            logger.exception("Keystone unauthorized for user: %s", username_or_email)
            return (None, "Invalid username or password")

        if user_id is None:
            return (None, "Invalid username or password")

        try:
            admin_client, _ = self._get_client(
                self.admin_username, self.admin_password, self.admin_tenant
            )
            user = admin_client.users.get(user_id)
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized admin")
            return (None, "Keystone admin credentials are invalid: %s" % str(kut))

        if self.requires_email and not hasattr(user, "email"):
            return (None, "Missing email field for user %s" % user_id)

        email = user.email if hasattr(user, "email") else None
        return (UserInformation(username=user.name, email=email, id=user_id), None)

    def query_users(self, query, limit=20):
        return (None, self.federated_service, "Unsupported in Keystone V2")

    def get_user(self, username_or_email):
        return (None, "Unsupported in Keystone V2")


class KeystoneV3Users(FederatedUsers):
    """
    Delegates authentication to OpenStack Keystone V3.
    """

    def __init__(
        self,
        auth_url,
        admin_username,
        admin_password,
        admin_tenant,
        timeout=None,
        requires_email=True,
        project_domain_id="default",
        user_domain_id="default",
    ):
        super(KeystoneV3Users, self).__init__("keystone", requires_email)
        self.auth_url = auth_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_tenant = admin_tenant
        self.project_domain_id = project_domain_id
        self.user_domain_id = user_domain_id
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.debug = os.environ.get("USERS_DEBUG") == "1"
        self.requires_email = requires_email

    def _get_client(self, username, password, project_name=None):
        if project_name:
            auth = keystone_v3_auth.Password(
                auth_url=self.auth_url,
                username=username,
                password=password,
                project_name=project_name,
                project_domain_id=self.project_domain_id,
                user_domain_id=self.user_domain_id,
            )
        else:
            auth = keystone_v3_auth.Password(
                auth_url=self.auth_url,
                username=username,
                password=password,
                user_domain_id=self.user_domain_id,
            )

        sess = session.Session(auth=auth)
        client = client_v3.Client(session=sess, timeout=self.timeout, debug=self.debug)
        return client, sess

    def ping(self):
        try:
            _, sess = self._get_client(self.admin_username, self.admin_password)
            assert sess.get_user_id()  # Make sure we loaded a valid user.
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized admin")
            return (False, "Keystone admin credentials are invalid: %s" % str(kut))
        except ClientException as cle:
            logger.exception("Keystone unauthorized admin")
            return (False, "Keystone ping check failed: %s" % str(cle))

        return (True, None)

    def at_least_one_user_exists(self):
        logger.debug("Checking if any users exist in admin tenant in Keystone")
        try:
            # Just make sure the admin can connect to the project.
            self._get_client(self.admin_username, self.admin_password, self.admin_tenant)
            return (True, None)
        except ClientException as cle:
            # Catch exceptions to give the user our custom error message
            logger.exception("Unable to list users in Keystone")
            return (False, str(cle))

    def verify_credentials(self, username_or_email, password):
        try:
            keystone_client, sess = self._get_client(username_or_email, password)
            user_id = sess.get_user_id()
            assert user_id

            keystone_client, sess = self._get_client(
                self.admin_username, self.admin_password, self.admin_tenant
            )
            user = keystone_client.users.get(user_id)
            if self.requires_email and not hasattr(user, "email"):
                return (None, "Missing email field for user %s" % user_id)

            return (self._user_info(user), None)
        except KeystoneAuthorizationFailure as kaf:
            logger.exception("Keystone auth failure for user: %s", username_or_email)
            return (None, "Invalid username or password")
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized for user: %s", username_or_email)
            return (None, "Invalid username or password")
        except ClientException as cle:
            logger.exception("Keystone unauthorized for user: %s", username_or_email)
            return (None, "Invalid username or password")

    def get_user(self, username_or_email):
        users_found, _, err_msg = self.query_users(username_or_email)
        if err_msg is not None:
            return (None, err_msg)

        if len(users_found) != 1:
            return (None, "Single user not found")

        user = users_found[0]
        if self.requires_email and not user.email:
            return (None, "Missing email field for user %s" % user.id)

        return (user, None)

    def check_group_lookup_args(self, group_lookup_args):
        if not group_lookup_args.get("group_id"):
            return (False, "Missing group_id")

        group_id = group_lookup_args["group_id"]
        return self._check_group(group_id)

    def _check_group(self, group_id):
        try:
            admin_client, _ = self._get_client(
                self.admin_username, self.admin_password, self.admin_tenant
            )
            return (bool(admin_client.groups.get(group_id)), None)
        except KeystoneNotFound:
            return (False, "Group not found")
        except KeystoneAuthorizationFailure as kaf:
            logger.exception("Keystone auth failure for admin user for group lookup %s", group_id)
            return (False, str(kaf) or "Invalid admin username or password")
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized for admin user for group lookup %s", group_id)
            return (False, str(kut) or "Invalid admin username or password")
        except ClientException as cle:
            logger.exception("Keystone unauthorized for admin user for group lookup %s", group_id)
            return (False, str(cle) or "Invalid admin username or password")

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        group_id = group_lookup_args["group_id"]

        (status, err) = self._check_group(group_id)
        if not status:
            return (None, err)

        try:
            admin_client, _ = self._get_client(
                self.admin_username, self.admin_password, self.admin_tenant
            )
            user_info_iterator = admin_client.users.list(group=group_id)

            def iterator():
                for user in user_info_iterator:
                    yield (self._user_info(user), None)

            return (iterator(), None)
        except KeystoneAuthorizationFailure as kaf:
            logger.exception("Keystone auth failure for admin user for group lookup %s", group_id)
            return (False, str(kaf) or "Invalid admin username or password")
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized for admin user for group lookup %s", group_id)
            return (False, str(kut) or "Invalid admin username or password")
        except ClientException as cle:
            logger.exception("Keystone unauthorized for admin user for group lookup %s", group_id)
            return (False, str(cle) or "Invalid admin username or password")

    @staticmethod
    def _user_info(user):
        email = user.email if hasattr(user, "email") else None
        return UserInformation(user.name, email, user.id)

    def query_users(self, query, limit=20):
        if len(query) < 3:
            return ([], self.federated_service, None)

        try:
            admin_client, _ = self._get_client(
                self.admin_username, self.admin_password, self.admin_tenant
            )

            found_users = list(take(limit, admin_client.users.list(name=query)))
            logger.debug("For Keystone query %s found users: %s", query, found_users)
            if not found_users:
                return ([], self.federated_service, None)

            return ([self._user_info(user) for user in found_users], self.federated_service, None)
        except KeystoneAuthorizationFailure as kaf:
            logger.exception("Keystone auth failure for admin user for query %s", query)
            return (
                None,
                self.federated_service,
                str(kaf) or "Invalid admin username or password",
            )
        except KeystoneUnauthorized as kut:
            logger.exception("Keystone unauthorized for admin user for query %s", query)
            return (
                None,
                self.federated_service,
                str(kut) or "Invalid admin username or password",
            )
        except ClientException as cle:
            logger.exception("Keystone unauthorized for admin user for query %s", query)
            return (
                None,
                self.federated_service,
                str(cle) or "Invalid admin username or password",
            )
