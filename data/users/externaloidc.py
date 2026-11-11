import json
import logging
from urllib.parse import urlparse

from peewee import IntegrityError

import app
import features
from data import model
from data.database import db
from data.model import InvalidTeamException, UserAlreadyInTeam, team, user
from data.users.federated import DISABLED_MESSAGE, FederatedUsers, UserInformation
from data.users.shared import can_create_user
from oauth.login_utils import get_username_from_userinfo
from oauth.oidc import OIDCLoginService
from util.validation import generate_valid_usernames

logger = logging.getLogger(__name__)


class OIDCUsers(FederatedUsers):
    def __init__(
        self,
        client_id,
        client_secret,
        oidc_server,
        service_name,
        login_scopes,
        preferred_group_claim_name,
        requires_email=True,
        oidc_superuser_group=None,
        oidc_global_readonly_superuser_group=None,
    ):
        super(OIDCUsers, self).__init__("oidc", requires_email)
        self._client_id = client_id
        self._client_secret = client_secret
        self._oidc_server = oidc_server
        self._service_name = service_name
        self._login_scopes = login_scopes
        self._preferred_group_claim_name = preferred_group_claim_name
        self._requires_email = requires_email
        self._oidc_superuser_group = oidc_superuser_group
        self._oidc_global_readonly_superuser_group = oidc_global_readonly_superuser_group

    def service_metadata(self):
        for service in app.oauth_login.services:
            if isinstance(service, OIDCLoginService):
                return {"issuer_domain": urlparse(service.get_issuer()).netloc}
        return {}

    def is_superuser(self, username: str):
        """
        Initiated from FederatedUserManager.is_superuser(), falls back to ConfigUserManager.is_superuser()
        """
        return None

    def is_global_readonly_superuser(self, username: str):
        """
        Initiated from FederatedUserManager.is_global_readonly_superuser(), falls back to ConfigUserManager.is_global_readonly_superuser()
        """
        return None

    def is_restricted_user(self, username):
        """
        Checks whether the currently logged in user is restricted.
        """
        return None

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        """
        Used by teamSync worker, unsupported for oidc team sync
        """
        return (None, "Not supported")

    def has_password_set(self, username):
        # OIDC users authenticate via token flows; they have no Quay-local password.
        # Returning False lets require_fresh_login bypass the fresh-login check so
        # OIDC browser users are not prompted for a password they cannot provide.
        return False

    def _verify_credentials_and_service(self, username_or_email, password):
        """
        Same as `verify_credentials`, but also returns the OIDCLoginService that
        validated the credentials, so callers can scope identity lookups to the
        issuing provider.
        """
        if not password:
            return (None, None, "Anonymous binding not allowed.")

        if not username_or_email:
            return (None, None, "Missing username or email.")

        for service in app.oauth_login.services:
            if isinstance(service, OIDCLoginService):
                try:
                    response = service.password_grant_for_login(username_or_email, password)

                    if response is None:
                        return (None, None, "External OIDC Group Sync: Got no user info")

                    user_info = service.get_user_info(
                        service._http_client, response["access_token"]
                    )

                    # Verify for impersonation, matching the browser flow's
                    # safeguard in get_sub_username_email_from_token
                    # (oauth/login_utils.py).
                    if user_info.get("impersonated", False):
                        logger.debug("Requests from impersonated principals are not supported")
                        return (
                            None,
                            None,
                            "Requests from impersonated principals are not supported",
                        )

                    # When the provider returns an id_token with the password
                    # grant, verify that its sub matches the userinfo sub,
                    # mirroring the browser flow's check in
                    # get_sub_username_email_from_token (oauth/login_utils.py):
                    # a mismatching userinfo response must not be used to
                    # select or link an account. A token that fails to decode
                    # is surfaced by the exception handler below.
                    id_token = response.get("id_token")
                    if id_token:
                        decoded_id_token = service.decode_user_jwt(id_token)
                        if user_info.get("sub") != decoded_id_token.get("sub"):
                            logger.debug(
                                "Mismatch in `sub` returned by OIDC user info endpoint: %s vs %s",
                                user_info.get("sub"),
                                decoded_id_token.get("sub"),
                            )
                            return (
                                None,
                                None,
                                "Mismatch in `sub` returned by OIDC user info endpoint",
                            )

                    # Apply the same verified-email rule as the browser flow
                    # (get_sub_username_email_from_token in
                    # oauth/login_utils.py): only trust the e-mail claim when
                    # the provider marks it verified, or when it comes from the
                    # configured verified-e-mail claim. An unverified address
                    # must not be used to create an account or to satisfy the
                    # e-mail agreement checked when upgrading a legacy binding.
                    if service.config.get("VERIFIED_EMAIL_CLAIM_NAME"):
                        email_address = user_info.get(service.config["VERIFIED_EMAIL_CLAIM_NAME"])
                    else:
                        email_address = (
                            user_info.get("email") if user_info.get("email_verified") else None
                        )

                    return (
                        UserInformation(
                            username=get_username_from_userinfo(user_info, service.config),
                            email=email_address,
                            id=user_info.get("sub"),
                        ),
                        service,
                        None,
                    )
                except Exception as err:
                    logger.exception(
                        f"External OIDC Group Sync: Exception while verifying credentials: {err}"
                    )
                    return (None, None, err)

        return (None, None, None)

    def verify_credentials(self, username_or_email, password):
        """
        Unsupported to login via username/email and password
        """
        credentials, _, err_msg = self._verify_credentials_and_service(username_or_email, password)
        return (credentials, err_msg)

    def verify_and_link_user(self, username_or_email, password):
        """
        Verifies the given credentials against the configured OIDC provider and
        links the resulting identity to a database user.

        Users provisioned via the OIDC browser flow are bound to the provider's
        login service by their `sub` claim (see `_conduct_oauth_login` in
        oauth/login_utils.py), not to the internal `oidc` service by username.
        Match that binding first so that a password login for such a user
        (registry basic auth, `/api/v1/signin`) succeeds instead of attempting
        to re-create the account and failing with "Email has already been
        used".

        When no `(provider, sub)` binding exists yet, link by `sub` as well
        (`_link_federated_login_by_sub`) so that accounts first provisioned by
        a password login use the same identity key the browser flow matches.
        The base-class fallback instead binds the internal `oidc` service by
        username, a key the browser callback can never match — whichever flow
        provisions the account first, the other then fails with the same
        "Email has already been used" error.
        """
        credentials, service, err_msg = self._verify_credentials_and_service(
            username_or_email, password
        )
        if credentials is None:
            return (None, err_msg)

        if credentials.id and service is not None:
            # Parity with the browser flow: when the login service requires a
            # verified e-mail (FEATURE_MAILING on its login config), reject
            # before matching a binding rather than logging in an identity
            # without one.
            if service._mailing and credentials.email is None:
                return (
                    None,
                    "A verified email address is required to login with this service",
                )

            db_user = user.verify_federated_login(service.service_id(), credentials.id)
            if db_user is not None:
                return (db_user, None)

            return self._link_federated_login_by_sub(credentials, service)

        return self._get_and_link_federated_user_info(credentials.username, credentials.email)

    def _link_federated_login_by_sub(self, credentials, service):
        """
        Links the verified identity to a database user under the provider's login
        service with the `sub` claim as the identity, mirroring the key the OIDC
        browser flow binds (see `_conduct_oauth_login` in oauth/login_utils.py).

        The base-class fallback (`_get_and_link_federated_user_info`) instead binds
        the internal `oidc` service by username — a key the browser callback never
        looks up — so an account first provisioned by a password login could not
        complete a browser login: it fails with "Email has already been used".
        """
        service_id = service.service_id()

        # An account created by the pre-fix password-login path is bound to the
        # internal `oidc` service by username. Attach the (provider, sub) binding
        # so the browser flow can match it too. The provider-verified e-mail must
        # agree with the e-mail on the existing binding before it is upgraded; a
        # missing e-mail cannot establish that agreement. The legacy binding is
        # kept so other flows relying on it are unaffected.
        db_user = user.verify_federated_login(self._federated_service, credentials.username)
        if db_user is not None:
            if credentials.email and db_user.email == credentials.email:
                user.attach_federated_login(db_user, service_id, credentials.id)
                return (db_user, None)

        # No usable binding: create the account bound by (provider, sub), exactly
        # as a first browser login would. Creation checks mirror the base class
        # (`_get_and_link_federated_user_info`).
        blacklisted_domains = model.config.app_config.get("BLACKLISTED_EMAIL_DOMAINS")
        if not can_create_user(credentials.email, blacklisted_domains):
            return (None, DISABLED_MESSAGE)

        valid_username = None
        for valid_username in generate_valid_usernames(credentials.username):
            if model.user.is_username_unique(valid_username):
                break

        if not valid_username:
            logger.error("Unable to pick a username for user: %s", credentials.username)
            return (
                None,
                "Unable to pick a username. Please report this to your administrator.",
            )

        prompts = model.user.get_default_user_prompts(features)
        try:
            # create_user_noverify only checks e-mail uniqueness when
            # email_required is set (tied to MAILING here); check any nonempty
            # e-mail explicitly so a verified address owned by another user
            # returns the collision error instead of an unhandled database
            # error when MAILING is disabled.
            if credentials.email and model.user.find_user_by_email(credentials.email):
                raise model.InvalidEmailAddressException(
                    "Email has already been used: %s" % credentials.email
                )

            db_user = model.user.create_federated_user(
                valid_username,
                credentials.email,
                service_id,
                credentials.id,
                set_password_notification=False,
                email_required=features.MAILING,
                confirm_username=features.USERNAME_CONFIRMATION,
                prompts=prompts,
            )
        except model.InvalidEmailAddressException as iae:
            return (None, str(iae))

        # Also attach the internal `oidc` binding by username, matching what
        # the pre-fix password path created, so `confirm_existing_user` (which
        # looks up the internal service) keeps working for accounts first
        # provisioned here. Best-effort: the ident may already belong to
        # another account when the legacy upgrade above was skipped due to an
        # e-mail mismatch.
        if credentials.username:
            try:
                # A nested atomic block (savepoint when inside a transaction) so
                # a failure rolls back only this insert and does not abort the
                # caller's transaction.
                with db.atomic():
                    model.user.attach_federated_login(
                        db_user, self._federated_service, credentials.username
                    )
            except IntegrityError:
                logger.debug(
                    "Unable to attach internal %s binding for username %s: already in use",
                    self._federated_service,
                    credentials.username,
                )

        return (db_user, None)

    def check_group_lookup_args(self, group_lookup_args, disable_pagination=False):
        """
        No way to verify if the group is valid, so assuming the group is valid
        """
        return (True, None)

    def get_user(self, username_or_email):
        """
        No way to look up a username or email in OIDC so returning None
        """
        return (None, "Currently user lookup is not supported with OIDC")

    def query_users(self, query, limit):
        """
        No way to query users so returning empty list
        """
        return ([], self._federated_service, "Not supported")

    def sync_oidc_groups(self, user_groups, user_obj):
        """
        Adds user to quay teams that have team sync enabled with an OIDC group
        """
        if not user_groups:
            if user_groups is None:
                logger.debug(
                    "External OIDC Group Sync: No group claim found for user: %s - check PREFERRED_GROUP_CLAIM_NAME",
                    user_obj.username,
                )
            else:
                logger.debug(
                    "External OIDC Group Sync: Found no oidc groups for user: %s", user_obj.username
                )
            return

        # fetch all TeamSync rows for the oidc_group synced with the login service
        synced_teams = team.get_oidc_teams_from_groupname(user_groups, self._federated_service)
        if len(synced_teams) == 0:
            logger.debug("External OIDC Group Sync: No teams with OIDC syncing groups found")
            return

        logger.debug(
            "External OIDC Group Sync: Syncing user %s with %s groups: %s",
            user_obj.username,
            len(synced_teams),
            [t.team.name for t in synced_teams],
        )

        # fetch team name and organization name for the Teamsync row
        for team_synced in synced_teams:
            team_name = team_synced.team.name
            org_name = team_synced.team.organization.username
            if not team_name or not org_name:
                continue

            # add user to team
            try:
                team.add_user_to_team(user_obj, team_synced.team)
            except InvalidTeamException as err:
                logger.exception(
                    "External OIDC Group Sync: Exception occurred when adding user %s to quay team %s: %s",
                    user_obj.username,
                    team_synced.team,
                    err,
                )
            except UserAlreadyInTeam:
                # Ignore
                pass
        return

    def ping(self):
        """
        TODO: get the OIDC connection here
        """
        return (True, None)

    def resync_quay_teams(self, user_groups, user_obj):
        """
        Fetch quay teams that user is a member of.
        Remove user from teams that are synced with an OIDC group but group does not exist in "user_groups"
        """
        # fetch user's quay teams that have team sync enabled
        existing_user_teams = team.get_federated_user_teams(user_obj, self._federated_service)
        logger.debug(
            f"External OIDC Group Sync: For user {user_obj.username} re-syncing {len(existing_user_teams)} quay teams"
        )
        user_groups = user_groups or []
        for user_team in existing_user_teams:
            try:
                sync_group_info = json.loads(user_team.teamsync.config)
                # remove user's membership from teams that were not returned from users OIDC groups
                if (
                    sync_group_info.get("group_name", None)
                    and sync_group_info["group_name"] not in user_groups
                ):
                    org_name = user_team.teamsync.team.organization.username
                    team.remove_user_from_team(org_name, user_team.name, user_obj.username, None)
                    logger.debug(
                        f"External OIDC Group Sync: Successfully removed user: {user_obj.username} from team: {user_team.name} in organization: {org_name}"
                    )
            except Exception as err:
                logger.exception(
                    f"External OIDC Group Sync: Exception occurred for user {user_obj.username} when removing membership from quay team: {user_team.name} as {err}"
                )
        return

    def sync_superuser_status(self, user_groups, user_obj):
        """
        Syncs superuser and global readonly superuser status based on OIDC group membership.
        Registers or deregisters the user via the shared ConfigUserManager arrays.
        """
        if not user_obj or user_groups is None:
            return

        try:
            if self._oidc_superuser_group:
                if user_groups and self._oidc_superuser_group in user_groups:
                    logger.debug(
                        "OIDC superuser sync: granting superuser to %s (member of %s)",
                        user_obj.username,
                        self._oidc_superuser_group,
                    )
                    app.usermanager.register_superuser(user_obj.username)
                else:
                    logger.debug(
                        "OIDC superuser sync: revoking superuser from %s (not member of %s)",
                        user_obj.username,
                        self._oidc_superuser_group,
                    )
                    app.usermanager.deregister_superuser(user_obj.username)

            if self._oidc_global_readonly_superuser_group:
                if user_groups and self._oidc_global_readonly_superuser_group in user_groups:
                    logger.debug(
                        "OIDC superuser sync: granting global readonly superuser to %s (member of %s)",
                        user_obj.username,
                        self._oidc_global_readonly_superuser_group,
                    )
                    app.usermanager.register_global_readonly_superuser(user_obj.username)
                else:
                    logger.debug(
                        "OIDC superuser sync: revoking global readonly superuser from %s (not member of %s)",
                        user_obj.username,
                        self._oidc_global_readonly_superuser_group,
                    )
                    app.usermanager.deregister_global_readonly_superuser(user_obj.username)
        except Exception:
            logger.exception(
                "OIDC superuser sync: failed to sync superuser status for %s",
                user_obj.username,
            )

    def sync_user_groups(self, user_groups, user_obj, login_service):
        if not user_obj:
            return

        self.sync_oidc_groups(user_groups, user_obj)
        self.resync_quay_teams(user_groups, user_obj)
        return
