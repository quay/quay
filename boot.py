#!/usr/bin/env python

import logging
import os.path
from datetime import datetime, timedelta
from urllib.parse import urlunparse

from cachetools.func import lru_cache
from cryptography.hazmat.primitives import serialization
from jinja2 import Template

import release
from _init import CONF_DIR
from app import app
from data.logs_model import logs_model
from data.model import ServiceKeyDoesNotExist, db_transaction
from data.model.oauth import (
    create_oauth_api_token,
    delete_other_bootstrap_tokens,
    delete_token_by_id,
    get_bootstrap_app_name,
    get_bootstrap_tokens,
    get_or_create_bootstrap_application,
    lock_bootstrap_token_operation,
    lookup_application_by_name,
    validate_bootstrap_token,
)
from data.model.release import set_region_release
from data.model.service_keys import get_service_key
from data.model.user import get_user
from util.bootstrap_token import read_bootstrap_token, write_bootstrap_token
from util.config.database import sync_database_with_config
from util.generatepresharedkey import generate_key

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_audience():
    scheme = app.config.get("PREFERRED_URL_SCHEME")
    hostname = app.config.get("SERVER_HOSTNAME")

    # hostname includes port, use that
    if ":" in hostname:
        return urlunparse((scheme, hostname, "", "", "", ""))

    # no port, guess based on scheme
    if scheme == "https":
        port = "443"
    else:
        port = "80"

    return urlunparse((scheme, hostname + ":" + port, "", "", "", ""))


def _verify_service_key():
    try:
        with open(app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"]) as f:
            quay_key_id = f.read()

        try:
            get_service_key(quay_key_id, approved_only=False)
            assert os.path.exists(app.config["INSTANCE_SERVICE_KEY_LOCATION"])
            return quay_key_id
        except ServiceKeyDoesNotExist:
            logger.exception(
                "Could not find non-expired existing service key %s; creating a new one",
                quay_key_id,
            )
            return None

        # Found a valid service key, so exiting.
    except IOError:
        logger.exception("Could not load existing service key; creating a new one")
        return None


def setup_instance_service_key():
    """
    Creates a service key for quay.
    """
    # Ensure we have an existing key if in read-only mode.
    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        quay_key_id = _verify_service_key()
        if quay_key_id is None:
            raise Exception("No valid service key found for read-only registry.")
    else:
        # Generate the key for this Quay instance to use.
        minutes_until_expiration = app.config.get("INSTANCE_SERVICE_KEY_EXPIRATION", 120)
        expiration = datetime.utcnow() + timedelta(minutes=minutes_until_expiration)
        quay_key, quay_key_id = generate_key(
            app.config["INSTANCE_SERVICE_KEY_SERVICE"], get_audience(), expiration_date=expiration
        )

        with open(app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"], mode="w") as f:
            f.truncate(0)
            f.write(quay_key_id)

        with open(app.config["INSTANCE_SERVICE_KEY_LOCATION"], mode="wb") as f:
            f.truncate(0)
            f.write(
                quay_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )


def setup_bootstrap_token():
    """Provision or revoke the bootstrap token based on FEATURE_PROGRAMMATIC_BOOTSTRAP."""
    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        logger.debug("Registry is in read-only mode, skipping bootstrap token setup")
        return

    if app.config.get("FEATURE_PROGRAMMATIC_BOOTSTRAP", False):
        _provision_bootstrap_token()
    else:
        _revoke_bootstrap_tokens()


def _get_valid_bootstrap_token_from_store():
    try:
        access_token = read_bootstrap_token(app.config)
    except OSError:
        logger.exception("Could not read stored bootstrap token; attempting to rewrite it")
        return None

    if not access_token:
        return None

    token = validate_bootstrap_token(access_token, app.config)
    if token is None:
        logger.warning("Stored bootstrap token is invalid; rewriting it")
        return None

    return token


def _get_bootstrap_token_owner_user():
    owner_name = app.config.get("BOOTSTRAP_TOKEN_OWNER")
    if not owner_name:
        raise Exception(
            "BOOTSTRAP_TOKEN_OWNER must be set when FEATURE_PROGRAMMATIC_BOOTSTRAP is enabled"
        )

    superusers = app.config.get("SUPER_USERS") or []
    if owner_name not in superusers:
        raise Exception("BOOTSTRAP_TOKEN_OWNER must be listed in SUPER_USERS")

    owner = get_user(owner_name)
    if owner is None:
        logger.error(
            "Bootstrap token owner '%s' was not found in the database; "
            "skipping bootstrap token provisioning",
            owner_name,
        )
        return None

    return owner


def _provision_bootstrap_token():
    superuser = _get_bootstrap_token_owner_user()
    if superuser is None:
        return

    scope = app.config["PROGRAMMATIC_TOKEN_SCOPE"]
    expiration = app.config["PROGRAMMATIC_TOKEN_EXPIRATION"]
    bootstrap_app_name = get_bootstrap_app_name(app.config)

    token_record = None
    try:
        with db_transaction():
            # Serialize all bootstrap token mutations through a transaction-scoped
            # advisory lock. Token ownership comes from BOOTSTRAP_TOKEN_OWNER, so
            # SUPER_USERS ordering does not determine which row is locked.
            # The write is intentionally inside the transaction to close the crash
            # window between DB commit and token store write.
            lock_bootstrap_token_operation()

            application = get_or_create_bootstrap_application(bootstrap_app_name, superuser)
            tokens = get_bootstrap_tokens(application)

            stored_token = _get_valid_bootstrap_token_from_store() if tokens else None
            token_ids = {token.id for token in tokens}
            if stored_token is not None and stored_token.id in token_ids:
                delete_other_bootstrap_tokens(application, keep_token_id=stored_token.id)
                logger.info("Bootstrap token already provisioned, skipping")
                return

            if tokens:
                logger.info("Stored bootstrap token missing or invalid; replacing stale DB tokens")
                delete_other_bootstrap_tokens(application)

            token_record, access_token = create_oauth_api_token(
                application, superuser, scope, expiration_seconds=expiration
            )
            write_bootstrap_token(app.config, access_token)
    except OSError:
        if token_record is not None:
            delete_token_by_id(token_record.id)
        logger.exception("Failed to write bootstrap token, rolled back")
        return

    logs_model.log_action(
        "create_oauth_api_token",
        superuser.username,
        metadata={
            "auth_method": "system_startup",
            "oauth_token_uuid": token_record.uuid,
            "scope": scope,
            "application_name": bootstrap_app_name,
        },
    )
    logger.info("Bootstrap token provisioned")


def _revoke_bootstrap_tokens():
    bootstrap_app_name = get_bootstrap_app_name(app.config)
    owner_name = app.config.get("BOOTSTRAP_TOKEN_OWNER")
    if not owner_name:
        return

    if owner_name not in (app.config.get("SUPER_USERS") or []):
        return

    owner = get_user(owner_name)
    if owner is None:
        return

    with db_transaction():
        lock_bootstrap_token_operation()
        application = lookup_application_by_name(owner, bootstrap_app_name)
        if application is None:
            return

        tokens = get_bootstrap_tokens(application)
        if not tokens:
            return

        performer = owner.username
        revoked = len(tokens)
        delete_other_bootstrap_tokens(application)

    if revoked == 0:
        return

    logs_model.log_action(
        "revoke_oauth_api_token",
        performer,
        metadata={
            "auth_method": "system_startup",
            "application_name": bootstrap_app_name,
        },
    )
    logger.info("Bootstrap tokens revoked (feature disabled)")


def main():
    if not app.config.get("SETUP_COMPLETE", False):
        raise Exception(
            "Your configuration bundle is either not mounted or setup has not been completed"
        )

    sync_database_with_config(app.config)
    setup_instance_service_key()
    setup_bootstrap_token()

    # Record deploy
    if release.REGION and release.GIT_HEAD:
        set_region_release(release.SERVICE, release.REGION, release.GIT_HEAD)


if __name__ == "__main__":
    main()
