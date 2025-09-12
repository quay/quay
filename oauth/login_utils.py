import logging
from collections import namedtuple

import jwt
from peewee import IntegrityError

import features
from data import model
from data.users.shared import can_create_user
from oauth.login import OAuthLoginException
from util.validation import generate_valid_usernames

OAuthResult = namedtuple(
    "OAuthResult",
    ["user_obj", "service_name", "error_message", "register_redirect", "requires_verification"],
)

logger = logging.getLogger(__name__)


def get_jwt_issuer(token):
    """
    Extract the issuer from the JWT token.
    The passed token is assumed to be a valid
    JWT token
    """
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded.get("iss", None)


def get_username_from_userinfo(user_info, config={}):
    # Check for a preferred username.
    if config.get("PREFERRED_USERNAME_CLAIM_NAME"):
        lusername = user_info.get(config["PREFERRED_USERNAME_CLAIM_NAME"])
    else:
        lusername = user_info.get("preferred_username")
        if lusername is None:
            # Note: Active Directory provides `unique_name` and `upn`.
            # https://docs.microsoft.com/en-us/azure/active-directory/develop/v1-id-and-access-tokens
            lusername = user_info.get("unique_name", user_info.get("upn"))

    if lusername is None:
        lusername = user_info["sub"]

    if lusername.find("@") >= 0:
        lusername = lusername[0 : lusername.find("@")]
    return lusername


def get_sub_username_email_from_token(
    decoded_id_token, user_info=None, config={}, mailing=False, fetch_groups=False
):
    if not user_info:
        user_info = decoded_id_token

    additional_info = {}
    # Verify for impersonation
    if user_info.get("impersonated", False):
        logger.debug("Requests from impersonated principals are not supported")
        raise OAuthLoginException("Requests from impersonated principals are not supported")

    # Verify subs.
    if user_info["sub"] != decoded_id_token["sub"]:
        logger.debug(
            "Mismatch in `sub` returned by OIDC user info endpoint: %s vs %s",
            user_info["sub"],
            decoded_id_token["sub"],
        )
        raise OAuthLoginException("Mismatch in `sub` returned by OIDC user info endpoint")

    # Check if we have a verified email address.
    if config.get("VERIFIED_EMAIL_CLAIM_NAME"):
        email_address = user_info.get(config["VERIFIED_EMAIL_CLAIM_NAME"])
    else:
        email_address = user_info.get("email") if user_info.get("email_verified") else None

    logger.debug("Found e-mail address `%s` for sub `%s`", email_address, user_info["sub"])

    if mailing:
        if email_address is None:
            raise OAuthLoginException(
                "A verified email address is required to login with this service"
            )
    lusername = get_username_from_userinfo(user_info, config)

    if fetch_groups:
        if config.get("PREFERRED_GROUP_CLAIM_NAME", None) is None:
            logger.exception(
                "PREFERRED_GROUP_CLAIM_NAME needs to be added in the config for teamsync via OIDC"
            )
        else:
            additional_info["groups"] = user_info.get(
                config.get("PREFERRED_GROUP_CLAIM_NAME", None)
            )

    return decoded_id_token["sub"], lusername, email_address, additional_info


def _oauthresult(
    user_obj=None,
    service_name=None,
    error_message=None,
    register_redirect=False,
    requires_verification=False,
):
    return OAuthResult(
        user_obj, service_name, error_message, register_redirect, requires_verification
    )


def _attach_service(config, login_service, user_obj, lid, lusername):
    """
    Attaches the given user account to the given service, with the given service user ID and service
    username.
    """
    metadata = {
        "service_username": lusername,
    }

    try:
        model.user.attach_federated_login(
            user_obj, login_service.service_id(), lid, metadata=metadata
        )
        return _oauthresult(user_obj=user_obj)
    except IntegrityError:
        err = "%s account %s is already attached to a %s account" % (
            login_service.service_name(),
            lusername,
            config["REGISTRY_TITLE_SHORT"],
        )
        return _oauthresult(service_name=login_service.service_name(), error_message=err)


def sync_oidc_groups(additional_login_info, user_obj, auth_system, login_service, config):
    if (
        config.get("AUTHENTICATION_TYPE", "oidc")
        and config.get("FEATURE_TEAM_SYNCING", False)
        and additional_login_info
    ):
        auth_system.sync_user_groups(additional_login_info.get("groups"), user_obj, login_service)
    return


def _conduct_oauth_login(
    config,
    analytics,
    auth_system,
    login_service,
    lid,
    lusername,
    lemail,
    metadata=None,
    captcha_verified=False,
    additional_login_info=None,
):
    """
    Conducts login from the result of an OAuth service's login flow and returns the status of the
    login, as well as the followup step.
    """
    service_id = login_service.service_id()
    service_name = login_service.service_name()

    # Check for an existing account *bound to this service*. If found, conduct login of that account
    # and redirect.
    user_obj = model.user.verify_federated_login(service_id, lid)
    if user_obj is not None:
        sync_oidc_groups(additional_login_info, user_obj, auth_system, login_service, config)
        return _oauthresult(user_obj=user_obj, service_name=service_name)

    # If the login service has a bound field name, and we have a defined internal auth type that is
    # not the database, then search for an existing account with that matching field. This allows
    # users to setup SSO while also being backed by something like LDAP.
    bound_field_name = login_service.login_binding_field()
    if auth_system.federated_service is not None and bound_field_name is not None:
        # Perform lookup.
        logger.debug('Got oauth bind field name of "%s"', bound_field_name)
        lookup_value = None
        if bound_field_name == "sub":
            lookup_value = lid
        elif bound_field_name == "username":
            lookup_value = lusername
        elif bound_field_name == "email":
            lookup_value = lemail

        if lookup_value is None:
            logger.error("Missing lookup value for OAuth login")
            return _oauthresult(
                service_name=service_name, error_message="Configuration error in this provider"
            )

        (user_obj, err) = auth_system.link_user(lookup_value)
        if err is not None:
            logger.debug("%s %s not found: %s", bound_field_name, lookup_value, err)
            msg = "%s %s not found in backing auth system" % (bound_field_name, lookup_value)
            return _oauthresult(service_name=service_name, error_message=msg)

        # Found an existing user. Bind their internal auth account to this service as well.
        result = _attach_service(config, login_service, user_obj, lid, lusername)
        if result.error_message is not None:
            return result

        sync_oidc_groups(additional_login_info, user_obj, auth_system, login_service, config)
        return _oauthresult(user_obj=user_obj, service_name=service_name)

    # Otherwise, we need to create a new user account.
    blacklisted_domains = config.get("BLACKLISTED_EMAIL_DOMAINS", [])
    if not can_create_user(lemail, blacklisted_domains=blacklisted_domains):
        error_message = "User creation is disabled. Please contact your administrator"
        return _oauthresult(service_name=service_name, error_message=error_message)

    if features.RECAPTCHA and not captcha_verified:
        return _oauthresult(service_name=service_name, requires_verification=True)

    # Try to create the user
    try:
        # Generate a valid username.
        new_username = None
        for valid in generate_valid_usernames(lusername):
            if model.user.get_user_or_org(valid):
                continue

            new_username = valid
            break

        requires_password = auth_system.requires_distinct_cli_password
        prompts = model.user.get_default_user_prompts(features)
        user_obj = model.user.create_federated_user(
            new_username,
            lemail,
            service_id,
            lid,
            set_password_notification=requires_password,
            metadata=metadata or {},
            confirm_username=features.USERNAME_CONFIRMATION,
            prompts=prompts,
            email_required=features.MAILING,
        )

        # Success, tell analytics
        analytics.track(user_obj.username, "register", {"service": service_name.lower()})
        sync_oidc_groups(additional_login_info, user_obj, auth_system, login_service, config)
        return _oauthresult(user_obj=user_obj, service_name=service_name)

    except model.InvalidEmailAddressException:
        message = (
            "The e-mail address {0} is already associated "
            "with an existing {1} account. \n"
            "Please log in with your username and password and "
            "associate your {2} account to use it in the future."
        )
        message = message.format(lemail, config["REGISTRY_TITLE_SHORT"], service_name)
        return _oauthresult(
            service_name=service_name, error_message=message, register_redirect=True
        )

    except model.DataModelException as ex:
        return _oauthresult(service_name=service_name, error_message=str(ex))
