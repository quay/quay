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
from data.model import ServiceKeyDoesNotExist, db_transaction
from data.model.oauth import (
    create_bootstrap_application,
    create_bootstrap_oauth_api_token,
    delete_applications,
    get_bootstrap_app_name,
    get_bootstrap_application_candidates,
    get_bootstrap_tokens,
    lock_bootstrap_token_operation,
    lookup_applications_by_name,
)
from data.model.release import set_region_release
from data.model.service_keys import get_service_key
from data.model.user import get_user
from util.bootstrap_token import delete_bootstrap_token, write_bootstrap_token
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
    """Provision or revoke the startup bootstrap token based on feature configuration."""
    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        logger.debug("Registry is in read-only mode, skipping bootstrap token setup")
        return

    if "FEATURE_PROGRAMMATIC_BOOTSTRAP" not in app.config:
        logger.debug("Programmatic bootstrap feature is not configured, skipping token setup")
        return

    if app.config["FEATURE_PROGRAMMATIC_BOOTSTRAP"]:
        logger.debug("FEATURE_PROGRAMMATIC_BOOTSTRAP is true, will attempt to use bootstrap token")
        _provision_bootstrap_token()
    else:
        logger.debug(
            "FEATURE_PROGRAMMATIC_BOOTSTRAP exists and is false, "
            "will attempt to delete the bootstrap token"
        )
        _revoke_bootstrap_tokens()


def _get_bootstrap_token_owner_user():
    owner_name = app.config.get("BOOTSTRAP_TOKEN_OWNER")
    if not owner_name:
        logger.error(
            "BOOTSTRAP_TOKEN_OWNER must be set when FEATURE_PROGRAMMATIC_BOOTSTRAP is enabled"
        )
        return None

    if owner_name not in (app.config.get("SUPER_USERS") or []):
        logger.error("BOOTSTRAP_TOKEN_OWNER must be listed in SUPER_USERS")
        return None

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
    owner = _get_bootstrap_token_owner_user()
    if owner is None:
        return

    scope = app.config["BOOTSTRAP_TOKEN_SCOPE"]
    expiration = app.config["BOOTSTRAP_TOKEN_EXPIRATION"]
    bootstrap_application_name = get_bootstrap_app_name(app.config)

    try:
        with db_transaction():
            lock_bootstrap_token_operation()

            bootstrap_application, duplicate_applications = get_bootstrap_application_candidates(
                owner,
                app_config=app.config,
            )
            if bootstrap_application is not None:
                if duplicate_applications:
                    delete_applications(duplicate_applications)
                    logger.info(
                        "Deleted %s duplicate bootstrap applications",
                        len(duplicate_applications),
                    )

                # Treat the database as the startup source of truth for Phase 1 local
                # host-file storage in standalone installations. In multi-node setups
                # using node-local files, this host may legitimately not have the file
                # that another host wrote. The plaintext token cannot be reconstructed
                # from the DB, so do not rotate or recreate it solely because the local
                # file is missing or malformed.
                logger.info("Bootstrap token already provisioned, skipping")
                return

            bootstrap_application = create_bootstrap_application(bootstrap_application_name, owner)
            _, access_token = create_bootstrap_oauth_api_token(
                bootstrap_application,
                owner,
                scope,
                expiration_seconds=expiration,
            )
            write_bootstrap_token(app.config, access_token)
            logger.info("Bootstrap token provisioned")
            return
    except OSError:
        logger.exception("Failed to write bootstrap token, rolled back")
        return


def _get_bootstrap_revocation_owners():
    owner_name = app.config.get("BOOTSTRAP_TOKEN_OWNER")
    owner = get_user(owner_name) if owner_name else None
    if owner is not None:
        return [owner]

    revocation_owners = []
    seen_usernames = set()
    for username in app.config.get("SUPER_USERS") or []:
        if username in seen_usernames:
            continue

        seen_usernames.add(username)
        super_user = get_user(username)
        if super_user is not None:
            revocation_owners.append(super_user)

    return revocation_owners


def _revoke_bootstrap_tokens():
    bootstrap_application_name = get_bootstrap_app_name(app.config)
    with db_transaction():
        lock_bootstrap_token_operation()

        bootstrap_applications = []
        for owner in _get_bootstrap_revocation_owners():
            applications = lookup_applications_by_name(owner, bootstrap_application_name)
            for application in applications:
                if get_bootstrap_tokens(application):
                    bootstrap_applications.append(application)

        delete_applications(bootstrap_applications)

    try:
        deleted_token_file = delete_bootstrap_token(app.config)
    except OSError:
        logger.exception("Failed to delete local bootstrap token file")
    else:
        if deleted_token_file:
            logger.info("Deleted local bootstrap token file")
        else:
            logger.debug("Local bootstrap token file did not exist, skipping deletion")

    logger.info(
        "Deleted %s bootstrap applications (feature disabled)",
        len(bootstrap_applications),
    )


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
