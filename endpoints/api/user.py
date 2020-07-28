"""
Manage the current user.
"""

import logging
import json
import recaptcha2

from flask import request, abort
from flask_login import logout_user
from flask_principal import identity_changed, AnonymousIdentity
from peewee import IntegrityError

import features

from app import (
    app,
    billing as stripe,
    authentication,
    avatar,
    all_queues,
    oauth_login,
    namespace_gc_queue,
    ip_resolver,
    url_scheme_and_hostname,
)

from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.permissions import (
    AdministerOrganizationPermission,
    CreateRepositoryPermission,
    UserAdminPermission,
    UserReadPermission,
    SuperUserPermission,
)
from data import model
from data.billing import get_plan
from data.database import Repository as RepositoryTable
from data.users.shared import can_create_user
from endpoints.api import (
    ApiResource,
    nickname,
    resource,
    validate_json_request,
    request_error,
    log_action,
    internal_only,
    require_user_admin,
    parse_args,
    query_param,
    require_scope,
    format_date,
    show_if,
    require_fresh_login,
    path_param,
    define_json_response,
    RepositoryParamResource,
    page_support,
)
from endpoints.exception import NotFound, InvalidToken, InvalidRequest, DownstreamIssue
from endpoints.api.subscribe import subscribe
from endpoints.common import common_login
from endpoints.csrf import generate_csrf_token, OAUTH_CSRF_TOKEN_NAME
from endpoints.decorators import anon_allowed, readonly_call_allowed
from oauth.oidc import DiscoveryFailureException
from util.useremails import (
    send_confirmation_email,
    send_recovery_email,
    send_change_email,
    send_password_changed,
    send_org_recovery_email,
)
from util.names import parse_single_urn
from util.request import get_request_ip


REPOS_PER_PAGE = 100


logger = logging.getLogger(__name__)


def handle_invite_code(invite_code, user):
    """
    Checks that the given invite code matches the specified user's e-mail address.

    If so, the user is marked as having a verified e-mail address and this method returns True.
    """
    parsed_invite = parse_single_urn(invite_code)
    if parsed_invite is None:
        return False

    if parsed_invite[0] != "teaminvite":
        return False

    # Check to see if the team invite is valid. If so, then we know the user has
    # a possible matching email address.
    try:
        found = model.team.find_matching_team_invite(invite_code, user)
    except model.DataModelException:
        return False

    # Since we sent the invite code via email, mark the user as having a verified
    # email address.
    if found.email != user.email:
        return False

    user.verified = True
    user.save()
    return True


def user_view(user, previous_username=None):
    def org_view(o, user_admin=True):
        admin_org = AdministerOrganizationPermission(o.username)
        org_response = {
            "name": o.username,
            "avatar": avatar.get_data_for_org(o),
            "can_create_repo": CreateRepositoryPermission(o.username).can(),
            "public": o.username in app.config.get("PUBLIC_NAMESPACES", []),
        }

        if user_admin:
            org_response.update(
                {"is_org_admin": admin_org.can(), "preferred_namespace": not (o.stripe_id is None),}
            )

        return org_response

    # Retrieve the organizations for the user.
    organizations = {
        o.username: o for o in model.organization.get_user_organizations(user.username)
    }

    # Add any public namespaces.
    public_namespaces = app.config.get("PUBLIC_NAMESPACES", [])
    if public_namespaces:
        organizations.update({ns: model.user.get_namespace_user(ns) for ns in public_namespaces})

    def login_view(login):
        try:
            metadata = json.loads(login.metadata_json)
        except:
            metadata = {}

        return {
            "service": login.service.name,
            "service_identifier": login.service_ident,
            "metadata": metadata,
        }

    logins = model.user.list_federated_logins(user)

    user_response = {
        "anonymous": False,
        "username": user.username,
        "avatar": avatar.get_data_for_user(user),
    }

    user_admin = UserAdminPermission(previous_username if previous_username else user.username)
    if user_admin.can():
        user_response.update(
            {
                "can_create_repo": True,
                "is_me": True,
                "verified": user.verified,
                "email": user.email,
                "logins": [login_view(login) for login in logins],
                "invoice_email": user.invoice_email,
                "invoice_email_address": user.invoice_email_address,
                "preferred_namespace": not (user.stripe_id is None),
                "tag_expiration_s": user.removed_tag_expiration_s,
                "prompts": model.user.get_user_prompts(user),
                "company": user.company,
                "family_name": user.family_name,
                "given_name": user.given_name,
                "location": user.location,
                "is_free_account": user.stripe_id is None,
                "has_password_set": authentication.has_password_set(user.username),
            }
        )

    user_view_perm = UserReadPermission(user.username)
    if user_view_perm.can():
        user_response.update(
            {
                "organizations": [
                    org_view(o, user_admin=user_admin.can()) for o in list(organizations.values())
                ],
            }
        )

    if features.SUPER_USERS and SuperUserPermission().can():
        user_response.update(
            {
                "super_user": user
                and user == get_authenticated_user()
                and SuperUserPermission().can()
            }
        )

    return user_response


def notification_view(note):
    return {
        "id": note.uuid,
        "organization": note.target.username if note.target.organization else None,
        "kind": note.kind.name,
        "created": format_date(note.created),
        "metadata": json.loads(note.metadata_json),
        "dismissed": note.dismissed,
    }


@resource("/v1/user/")
class User(ApiResource):
    """
    Operations related to users.
    """

    schemas = {
        "NewUser": {
            "type": "object",
            "description": "Fields which must be specified for a new user.",
            "required": ["username", "password",],
            "properties": {
                "username": {"type": "string", "description": "The user's username",},
                "password": {"type": "string", "description": "The user's password",},
                "email": {"type": "string", "description": "The user's email address",},
                "invite_code": {"type": "string", "description": "The optional invite code",},
                "recaptcha_response": {
                    "type": "string",
                    "description": "The (may be disabled) recaptcha response code for verification",
                },
            },
        },
        "UpdateUser": {
            "type": "object",
            "description": "Fields which can be updated in a user.",
            "properties": {
                "password": {"type": "string", "description": "The user's password",},
                "invoice_email": {
                    "type": "boolean",
                    "description": "Whether the user desires to receive an invoice email.",
                },
                "email": {"type": "string", "description": "The user's email address",},
                "tag_expiration_s": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "The number of seconds for tag expiration",
                },
                "username": {"type": "string", "description": "The user's username",},
                "invoice_email_address": {
                    "type": ["string", "null"],
                    "description": "Custom email address for receiving invoices",
                },
                "given_name": {
                    "type": ["string", "null"],
                    "description": "The optional entered given name for the user",
                },
                "family_name": {
                    "type": ["string", "null"],
                    "description": "The optional entered family name for the user",
                },
                "company": {
                    "type": ["string", "null"],
                    "description": "The optional entered company for the user",
                },
                "location": {
                    "type": ["string", "null"],
                    "description": "The optional entered location for the user",
                },
            },
        },
        "UserView": {
            "type": "object",
            "description": "Describes a user",
            "required": ["anonymous", "avatar"],
            "properties": {
                "verified": {
                    "type": "boolean",
                    "description": "Whether the user's email address has been verified",
                },
                "anonymous": {
                    "type": "boolean",
                    "description": "true if this user data represents a guest user",
                },
                "email": {"type": "string", "description": "The user's email address",},
                "avatar": {
                    "type": "object",
                    "description": "Avatar data representing the user's icon",
                },
                "organizations": {
                    "type": "array",
                    "description": "Information about the organizations in which the user is a member",
                    "items": {"type": "object"},
                },
                "logins": {
                    "type": "array",
                    "description": "The list of external login providers against which the user has authenticated",
                    "items": {"type": "object"},
                },
                "can_create_repo": {
                    "type": "boolean",
                    "description": "Whether the user has permission to create repositories",
                },
                "preferred_namespace": {
                    "type": "boolean",
                    "description": "If true, the user's namespace is the preferred namespace to display",
                },
            },
        },
    }

    @require_scope(scopes.READ_USER)
    @nickname("getLoggedInUser")
    @define_json_response("UserView")
    @anon_allowed
    def get(self):
        """
        Get user information for the authenticated user.
        """
        user = get_authenticated_user()
        if user is None or user.organization or not UserReadPermission(user.username).can():
            raise InvalidToken("Requires authentication", payload={"session_required": False})

        return user_view(user)

    @require_user_admin
    @require_fresh_login
    @nickname("changeUserDetails")
    @internal_only
    @validate_json_request("UpdateUser")
    def put(self):
        """
        Update a users details such as password or email.
        """
        user = get_authenticated_user()
        user_data = request.get_json()
        previous_username = None
        headers = None

        try:
            if "password" in user_data:
                logger.debug("Changing password for user: %s", user.username)
                log_action("account_change_password", user.username)

                # Change the user's password.
                model.user.change_password(user, user_data["password"])

                # Login again to reset their session cookie.
                success, headers = common_login(user.uuid)
                if not success:
                    raise request_error(message="Could not perform login action")

                if features.MAILING:
                    send_password_changed(user.username, user.email)

            if "invoice_email" in user_data:
                logger.debug("Changing invoice_email for user: %s", user.username)
                model.user.change_send_invoice_email(user, user_data["invoice_email"])

            if features.CHANGE_TAG_EXPIRATION and "tag_expiration_s" in user_data:
                logger.debug("Changing user tag expiration to: %ss", user_data["tag_expiration_s"])
                model.user.change_user_tag_expiration(user, user_data["tag_expiration_s"])

            if (
                "invoice_email_address" in user_data
                and user_data["invoice_email_address"] != user.invoice_email_address
            ):
                model.user.change_invoice_email_address(user, user_data["invoice_email_address"])

            if "email" in user_data and user_data["email"] != user.email:
                new_email = user_data["email"]
                if model.user.find_user_by_email(new_email):
                    # Email already used.
                    raise request_error(message="E-mail address already used")

                if features.MAILING:
                    logger.debug(
                        "Sending email to change email address for user: %s", user.username
                    )
                    confirmation_code = model.user.create_confirm_email_code(
                        user, new_email=new_email
                    )
                    send_change_email(user.username, user_data["email"], confirmation_code)
                else:
                    model.user.update_email(user, new_email, auto_verify=not features.MAILING)

            if features.USER_METADATA:
                metadata = {}

                for field in ("given_name", "family_name", "company", "location"):
                    if field in user_data:
                        metadata[field] = user_data.get(field)

                if len(metadata) > 0:
                    model.user.update_user_metadata(user, metadata)

            # Check for username rename. A username can be renamed if the feature is enabled OR the user
            # currently has a confirm_username prompt.
            if "username" in user_data:
                confirm_username = model.user.has_user_prompt(user, "confirm_username")
                new_username = user_data.get("username")
                previous_username = user.username

                rename_allowed = features.USER_RENAME or (
                    confirm_username and features.USERNAME_CONFIRMATION
                )
                username_changing = new_username and new_username != previous_username

                if rename_allowed and username_changing:
                    if model.user.get_user_or_org(new_username) is not None:
                        # Username already used.
                        raise request_error(message="Username is already in use")

                    user = model.user.change_username(user.id, new_username)
                elif confirm_username:
                    model.user.remove_user_prompt(user, "confirm_username")

        except model.user.InvalidPasswordException as ex:
            raise request_error(exception=ex)

        return user_view(user, previous_username=previous_username), 200, headers

    @show_if(features.USER_CREATION)
    @show_if(features.DIRECT_LOGIN)
    @nickname("createNewUser")
    @internal_only
    @validate_json_request("NewUser")
    def post(self):
        """
        Create a new user.
        """
        if app.config["AUTHENTICATION_TYPE"] != "Database":
            abort(404)

        user_data = request.get_json()

        invite_code = user_data.get("invite_code", "")
        existing_user = model.user.get_nonrobot_user(user_data["username"])
        if existing_user:
            raise request_error(message="The username already exists")

        # Ensure an e-mail address was specified if required.
        if features.MAILING and not user_data.get("email"):
            raise request_error(message="Email address is required")

        # If invite-only user creation is turned on and no invite code was sent, return an error.
        # Technically, this is handled by the can_create_user call below as well, but it makes
        # a nicer error.
        if features.INVITE_ONLY_USER_CREATION and not invite_code:
            raise request_error(message="Cannot create non-invited user")

        # Ensure that this user can be created.
        blacklisted_domains = app.config.get("BLACKLISTED_EMAIL_DOMAINS", [])
        if not can_create_user(user_data.get("email"), blacklisted_domains=blacklisted_domains):
            raise request_error(
                message="Creation of a user account for this e-mail is disabled; please contact an administrator"
            )

        # If recaptcha is enabled, then verify the user is a human.
        if features.RECAPTCHA:
            recaptcha_response = user_data.get("recaptcha_response", "")
            result = recaptcha2.verify(
                app.config["RECAPTCHA_SECRET_KEY"], recaptcha_response, get_request_ip()
            )

            if not result["success"]:
                return {"message": "Are you a bot? If not, please revalidate the captcha."}, 400

        is_possible_abuser = ip_resolver.is_ip_possible_threat(get_request_ip())
        try:
            prompts = model.user.get_default_user_prompts(features)
            new_user = model.user.create_user(
                user_data["username"],
                user_data["password"],
                user_data.get("email"),
                auto_verify=not features.MAILING,
                email_required=features.MAILING,
                is_possible_abuser=is_possible_abuser,
                prompts=prompts,
            )

            email_address_confirmed = handle_invite_code(invite_code, new_user)
            if features.MAILING and not email_address_confirmed:
                confirmation_code = model.user.create_confirm_email_code(new_user)
                send_confirmation_email(new_user.username, new_user.email, confirmation_code)
                return {"awaiting_verification": True}
            else:
                success, headers = common_login(new_user.uuid)
                if not success:
                    return {"message": "Could not login. Is your account inactive?"}, 403

                return user_view(new_user), 200, headers
        except model.user.DataModelException as ex:
            raise request_error(exception=ex)

    @require_user_admin
    @require_fresh_login
    @nickname("deleteCurrentUser")
    @internal_only
    def delete(self):
        """
        Deletes the current user.
        """
        if app.config["AUTHENTICATION_TYPE"] != "Database":
            abort(404)

        model.user.mark_namespace_for_deletion(
            get_authenticated_user(), all_queues, namespace_gc_queue
        )
        return "", 204


@resource("/v1/user/private")
@internal_only
@show_if(features.BILLING)
class PrivateRepositories(ApiResource):
    """
    Operations dealing with the available count of private repositories.
    """

    @require_user_admin
    @nickname("getUserPrivateAllowed")
    def get(self):
        """
        Get the number of private repos this user has, and whether they are allowed to create more.
        """
        user = get_authenticated_user()
        private_repos = model.user.get_private_repo_count(user.username)
        repos_allowed = 0

        if user.stripe_id:
            cus = stripe.Customer.retrieve(user.stripe_id)
            if cus.subscription:
                plan = get_plan(cus.subscription.plan.id)
                if plan:
                    repos_allowed = plan["privateRepos"]

        return {"privateCount": private_repos, "privateAllowed": (private_repos < repos_allowed)}


@resource("/v1/user/clientkey")
@internal_only
class ClientKey(ApiResource):
    """
    Operations for returning an encrypted key which can be used in place of a password for the
    Docker client.
    """

    schemas = {
        "GenerateClientKey": {
            "type": "object",
            "required": ["password",],
            "properties": {"password": {"type": "string", "description": "The user's password",},},
        }
    }

    @require_user_admin
    @nickname("generateUserClientKey")
    @validate_json_request("GenerateClientKey")
    def post(self):
        """
        Return's the user's private client key.
        """
        if not authentication.supports_encrypted_credentials:
            raise NotFound()

        username = get_authenticated_user().username
        password = request.get_json()["password"]
        (result, error_message) = authentication.confirm_existing_user(username, password)
        if not result:
            raise request_error(message=error_message)

        return {"key": authentication.encrypt_user_password(password).decode("ascii")}


def conduct_signin(username_or_email, password, invite_code=None):
    needs_email_verification = False
    invalid_credentials = False

    (found_user, error_message) = authentication.verify_and_link_user(username_or_email, password)
    if found_user:
        # If there is an attached invitation code, handle it here. This will mark the
        # user as verified if the code is valid.
        if invite_code:
            handle_invite_code(invite_code, found_user)

        success, headers = common_login(found_user.uuid)
        if success:
            return {"success": True}, 200, headers
        else:
            needs_email_verification = True

    else:
        invalid_credentials = True

    return (
        {
            "needsEmailVerification": needs_email_verification,
            "invalidCredentials": invalid_credentials,
            "message": error_message,
        },
        403,
        None,
    )


@resource("/v1/user/convert")
@internal_only
@show_if(app.config["AUTHENTICATION_TYPE"] == "Database")
class ConvertToOrganization(ApiResource):
    """
    Operations for converting a user to an organization.
    """

    schemas = {
        "ConvertUser": {
            "type": "object",
            "description": "Information required to convert a user to an organization.",
            "required": ["adminUser", "adminPassword"],
            "properties": {
                "adminUser": {
                    "type": "string",
                    "description": "The user who will become an org admin's username",
                },
                "adminPassword": {
                    "type": "string",
                    "description": "The user who will become an org admin's password",
                },
                "plan": {
                    "type": "string",
                    "description": "The plan to which the organization should be subscribed",
                },
            },
        },
    }

    @require_user_admin
    @nickname("convertUserToOrganization")
    @validate_json_request("ConvertUser")
    def post(self):
        """
        Convert the user to an organization.
        """
        user = get_authenticated_user()
        convert_data = request.get_json()

        # Ensure that the sign in credentials work.
        admin_username = convert_data["adminUser"]
        admin_password = convert_data["adminPassword"]
        (admin_user, _) = authentication.verify_and_link_user(admin_username, admin_password)
        if not admin_user:
            raise request_error(
                reason="invaliduser", message="The admin user credentials are not valid"
            )

        # Ensure that the new admin user is the not user being converted.
        if admin_user.id == user.id:
            raise request_error(reason="invaliduser", message="The admin user is not valid")

        # Subscribe the organization to the new plan.
        if features.BILLING:
            plan = convert_data.get("plan", "free")
            subscribe(user, plan, None, True)  # Require business plans

        # Convert the user to an organization.
        model.organization.convert_user_to_organization(user, admin_user)
        log_action("account_convert", user.username)

        # And finally login with the admin credentials.
        return conduct_signin(admin_username, admin_password)


@resource("/v1/signin")
@show_if(features.DIRECT_LOGIN)
@internal_only
class Signin(ApiResource):
    """
    Operations for signing in the user.
    """

    schemas = {
        "SigninUser": {
            "type": "object",
            "description": "Information required to sign in a user.",
            "required": ["username", "password",],
            "properties": {
                "username": {"type": "string", "description": "The user's username",},
                "password": {"type": "string", "description": "The user's password",},
                "invite_code": {"type": "string", "description": "The optional invite code"},
            },
        },
    }

    @nickname("signinUser")
    @validate_json_request("SigninUser")
    @anon_allowed
    @readonly_call_allowed
    def post(self):
        """
        Sign in the user with the specified credentials.
        """
        signin_data = request.get_json()
        if not signin_data:
            raise NotFound()

        username = signin_data["username"]
        password = signin_data["password"]
        invite_code = signin_data.get("invite_code", "")
        return conduct_signin(username, password, invite_code=invite_code)


@resource("/v1/signin/verify")
@internal_only
class VerifyUser(ApiResource):
    """
    Operations for verifying the existing user.
    """

    schemas = {
        "VerifyUser": {
            "id": "VerifyUser",
            "type": "object",
            "description": "Information required to verify the signed in user.",
            "required": ["password",],
            "properties": {"password": {"type": "string", "description": "The user's password",},},
        },
    }

    @require_user_admin
    @nickname("verifyUser")
    @validate_json_request("VerifyUser")
    @readonly_call_allowed
    def post(self):
        """
        Verifies the signed in the user with the specified credentials.
        """
        signin_data = request.get_json()
        password = signin_data["password"]

        username = get_authenticated_user().username
        (result, error_message) = authentication.confirm_existing_user(username, password)
        if not result:
            return {"message": error_message, "invalidCredentials": True,}, 403

        success, headers = common_login(result.uuid)
        if not success:
            return {"message": "Could not verify user.",}, 403

        return {"success": True}, 200, headers


@resource("/v1/signout")
@internal_only
class Signout(ApiResource):
    """
    Resource for signing out users.
    """

    @nickname("logout")
    def post(self):
        """
        Request that the current user be signed out.
        """
        # Invalidate all sessions for the user.
        model.user.invalidate_all_sessions(get_authenticated_user())

        # Clear out the user's identity.
        identity_changed.send(app, identity=AnonymousIdentity())

        # Remove the user's session cookie.
        logout_user()

        return {"success": True}


@resource("/v1/externallogin/<service_id>")
@internal_only
class ExternalLoginInformation(ApiResource):
    """
    Resource for both setting a token for external login and returning its authorization url.
    """

    schemas = {
        "GetLogin": {
            "type": "object",
            "description": "Information required to an retrieve external login URL.",
            "required": ["kind",],
            "properties": {
                "kind": {
                    "type": "string",
                    "description": "The kind of URL",
                    "enum": ["login", "attach", "cli"],
                },
            },
        },
    }

    @nickname("retrieveExternalLoginAuthorizationUrl")
    @anon_allowed
    @readonly_call_allowed
    @validate_json_request("GetLogin")
    def post(self, service_id):
        """
        Generates the auth URL and CSRF token explicitly for OIDC/OAuth-associated login.
        """
        login_service = oauth_login.get_service(service_id)
        if login_service is None:
            raise InvalidRequest()

        csrf_token = generate_csrf_token(OAUTH_CSRF_TOKEN_NAME)
        kind = request.get_json()["kind"]
        redirect_suffix = "" if kind == "login" else "/" + kind

        try:
            login_scopes = login_service.get_login_scopes()
            auth_url = login_service.get_auth_url(
                url_scheme_and_hostname, redirect_suffix, csrf_token, login_scopes
            )
            return {"auth_url": auth_url}
        except DiscoveryFailureException as dfe:
            logger.exception("Could not discovery OAuth endpoint information")
            raise DownstreamIssue(str(dfe))


@resource("/v1/detachexternal/<service_id>")
@show_if(features.DIRECT_LOGIN)
@internal_only
class DetachExternal(ApiResource):
    """
    Resource for detaching an external login.
    """

    @require_user_admin
    @nickname("detachExternalLogin")
    def post(self, service_id):
        """
        Request that the current user be detached from the external login service.
        """
        model.user.detach_external_login(get_authenticated_user(), service_id)
        return {"success": True}


@resource("/v1/recovery")
@show_if(features.MAILING)
@internal_only
class Recovery(ApiResource):
    """
    Resource for requesting a password recovery email.
    """

    schemas = {
        "RequestRecovery": {
            "type": "object",
            "description": "Information required to sign in a user.",
            "required": ["email",],
            "properties": {
                "email": {"type": "string", "description": "The user's email address",},
                "recaptcha_response": {
                    "type": "string",
                    "description": "The (may be disabled) recaptcha response code for verification",
                },
            },
        },
    }

    @nickname("requestRecoveryEmail")
    @anon_allowed
    @validate_json_request("RequestRecovery")
    def post(self):
        """
        Request a password recovery email.
        """

        def redact(value):
            threshold = max((len(value) / 3) - 1, 1)
            v = ""
            for i in range(0, len(value)):
                if i < threshold or i >= len(value) - threshold:
                    v = v + value[i]
                else:
                    v = v + "\u2022"

            return v

        recovery_data = request.get_json()

        # If recaptcha is enabled, then verify the user is a human.
        if features.RECAPTCHA:
            recaptcha_response = recovery_data.get("recaptcha_response", "")
            result = recaptcha2.verify(
                app.config["RECAPTCHA_SECRET_KEY"], recaptcha_response, get_request_ip()
            )

            if not result["success"]:
                return {"message": "Are you a bot? If not, please revalidate the captcha."}, 400

        email = recovery_data["email"]
        user = model.user.find_user_by_email(email)
        if not user:
            return {
                "status": "sent",
            }

        if user.organization:
            send_org_recovery_email(user, model.organization.get_admin_users(user))
            return {
                "status": "org",
                "orgemail": email,
                "orgname": redact(user.username),
            }

        confirmation_code = model.user.create_reset_password_email_code(email)
        send_recovery_email(email, confirmation_code)
        return {
            "status": "sent",
        }


@resource("/v1/user/notifications")
@internal_only
class UserNotificationList(ApiResource):
    @require_user_admin
    @parse_args()
    @query_param("page", "Offset page number. (int)", type=int, default=0)
    @query_param("limit", "Limit on the number of results (int)", type=int, default=5)
    @nickname("listUserNotifications")
    def get(self, parsed_args):
        page = parsed_args["page"]
        limit = parsed_args["limit"]

        notifications = list(
            model.notification.list_notifications(
                get_authenticated_user(), page=page, limit=limit + 1
            )
        )
        has_more = False

        if len(notifications) > limit:
            has_more = True
            notifications = notifications[0:limit]

        return {
            "notifications": [notification_view(note) for note in notifications],
            "additional": has_more,
        }


@resource("/v1/user/notifications/<uuid>")
@path_param("uuid", "The uuid of the user notification")
@internal_only
class UserNotification(ApiResource):
    schemas = {
        "UpdateNotification": {
            "type": "object",
            "description": "Information for updating a notification",
            "properties": {
                "dismissed": {
                    "type": "boolean",
                    "description": "Whether the notification is dismissed by the user",
                },
            },
        },
    }

    @require_user_admin
    @nickname("getUserNotification")
    def get(self, uuid):
        note = model.notification.lookup_notification(get_authenticated_user(), uuid)
        if not note:
            raise NotFound()

        return notification_view(note)

    @require_user_admin
    @nickname("updateUserNotification")
    @validate_json_request("UpdateNotification")
    def put(self, uuid):
        note = model.notification.lookup_notification(get_authenticated_user(), uuid)
        if not note:
            raise NotFound()

        note.dismissed = request.get_json().get("dismissed", False)
        note.save()

        return notification_view(note)


def authorization_view(access_token):
    oauth_app = access_token.application
    app_email = oauth_app.avatar_email or oauth_app.organization.email
    return {
        "application": {
            "name": oauth_app.name,
            "description": oauth_app.description,
            "url": oauth_app.application_uri,
            "avatar": avatar.get_data(oauth_app.name, app_email, "app"),
            "organization": {
                "name": oauth_app.organization.username,
                "avatar": avatar.get_data_for_org(oauth_app.organization),
            },
        },
        "scopes": scopes.get_scope_information(access_token.scope),
        "uuid": access_token.uuid,
    }


@resource("/v1/user/authorizations")
@internal_only
class UserAuthorizationList(ApiResource):
    @require_user_admin
    @nickname("listUserAuthorizations")
    def get(self):
        access_tokens = model.oauth.list_access_tokens_for_user(get_authenticated_user())

        return {"authorizations": [authorization_view(token) for token in access_tokens]}


@resource("/v1/user/authorizations/<access_token_uuid>")
@path_param("access_token_uuid", "The uuid of the access token")
@internal_only
class UserAuthorization(ApiResource):
    @require_user_admin
    @nickname("getUserAuthorization")
    def get(self, access_token_uuid):
        access_token = model.oauth.lookup_access_token_for_user(
            get_authenticated_user(), access_token_uuid
        )
        if not access_token:
            raise NotFound()

        return authorization_view(access_token)

    @require_user_admin
    @nickname("deleteUserAuthorization")
    def delete(self, access_token_uuid):
        access_token = model.oauth.lookup_access_token_for_user(
            get_authenticated_user(), access_token_uuid
        )
        if not access_token:
            raise NotFound()

        access_token.delete_instance(recursive=True, delete_nullable=True)
        return "", 204


@resource("/v1/user/starred")
class StarredRepositoryList(ApiResource):
    """
    Operations for creating and listing starred repositories.
    """

    schemas = {
        "NewStarredRepository": {
            "type": "object",
            "required": ["namespace", "repository",],
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace in which the repository belongs",
                },
                "repository": {"type": "string", "description": "Repository name"},
            },
        }
    }

    @nickname("listStarredRepos")
    @parse_args()
    @require_user_admin
    @page_support()
    def get(self, page_token, parsed_args):
        """
        List all starred repositories.
        """
        repo_query = model.repository.get_user_starred_repositories(get_authenticated_user())

        repos, next_page_token = model.modelutil.paginate(
            repo_query, RepositoryTable, page_token=page_token, limit=REPOS_PER_PAGE
        )

        def repo_view(repo_obj):
            return {
                "namespace": repo_obj.namespace_user.username,
                "name": repo_obj.name,
                "description": repo_obj.description,
                "is_public": model.repository.is_repository_public(repo_obj),
            }

        return {"repositories": [repo_view(repo) for repo in repos]}, next_page_token

    @require_scope(scopes.READ_REPO)
    @nickname("createStar")
    @validate_json_request("NewStarredRepository")
    @require_user_admin
    def post(self):
        """
        Star a repository.
        """
        user = get_authenticated_user()
        req = request.get_json()
        namespace = req["namespace"]
        repository = req["repository"]
        repo = model.repository.get_repository(namespace, repository)

        if repo:
            try:
                model.repository.star_repository(user, repo)
            except IntegrityError:
                pass

            return {"namespace": namespace, "repository": repository,}, 201


@resource("/v1/user/starred/<apirepopath:repository>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class StarredRepository(RepositoryParamResource):
    """
    Operations for managing a specific starred repository.
    """

    @nickname("deleteStar")
    @require_user_admin
    def delete(self, namespace, repository):
        """
        Removes a star from a repository.
        """
        user = get_authenticated_user()
        repo = model.repository.get_repository(namespace, repository)

        if repo:
            model.repository.unstar_repository(user, repo)
            return "", 204


@resource("/v1/users/<username>")
class Users(ApiResource):
    """
    Operations related to retrieving information about other users.
    """

    @nickname("getUserInformation")
    def get(self, username):
        """
        Get user information for the specified user.
        """
        user = model.user.get_nonrobot_user(username)
        if user is None:
            abort(404)

        return user_view(user)
