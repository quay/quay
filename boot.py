#!/usr/bin/env python

import logging
import os.path
from datetime import datetime, timedelta
from urllib.parse import urlunparse

from authlib.jose import JsonWebKey
from cachetools.func import lru_cache
from cryptography.hazmat.primitives import serialization
from jinja2 import Template
from peewee import IntegrityError

import release
from _init import CONF_DIR
from app import app
from data.database import ServiceKey, ServiceKeyApprovalType
from data.model import ServiceKeyAlreadyApproved, ServiceKeyDoesNotExist, db_transaction
from data.model.oauth import (
    create_bootstrap_application,
    create_bootstrap_oauth_api_token,
    delete_applications,
    get_bootstrap_app_name,
    get_bootstrap_managed_applications,
    get_singleton_bootstrap_application_candidates,
    lock_bootstrap_token_operation,
)
from data.model.release import set_region_release
from data.model.service_keys import (
    OPERATOR_MANAGED_CREATED_BY,
    approve_service_key,
    create_service_key,
    get_service_key,
)
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


def _load_mounted_key_material():
    """
    Reads the kid and PEM from the configured key file paths.
    Returns (kid, pem_data, public_jwk) or raises on failure.
    """
    kid_path = app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"]
    pem_path = app.config["INSTANCE_SERVICE_KEY_LOCATION"]

    with open(kid_path) as f:
        kid = f.read().strip()

    if not kid:
        raise Exception("Mounted key ID file is empty: %s" % kid_path)

    with open(pem_path, "rb") as f:
        pem_data = f.read()

    jwk_obj = JsonWebKey.import_key(pem_data)
    public_jwk = jwk_obj.as_dict()

    computed_kid = public_jwk.get("kid")
    if computed_kid != kid:
        raise Exception(
            "Mounted key ID '%s' does not match computed RFC 7638 thumbprint '%s'"
            % (kid, computed_kid)
        )

    return kid, pem_data, public_jwk


def _jwk_matches(jwk_a, jwk_b):
    return jwk_a.get("n") == jwk_b.get("n") and jwk_a.get("e") == jwk_b.get("e")


def _validate_existing_key(existing_key, kid, public_jwk, service):
    """
    Validates an existing DB key row against the mounted key material.
    Raises on mismatch. Backfills created_by metadata if absent.
    """
    if existing_key.service != service:
        raise Exception(
            "Existing key '%s' belongs to service '%s', expected '%s'"
            % (kid, existing_key.service, service)
        )

    if not _jwk_matches(existing_key.jwk, public_jwk):
        raise Exception(
            "Existing key '%s' public JWK does not match the mounted PEM-derived JWK" % kid
        )

    metadata = existing_key.metadata if isinstance(existing_key.metadata, dict) else {}
    created_by = metadata.get("created_by")

    if created_by and created_by != OPERATOR_MANAGED_CREATED_BY:
        raise Exception(
            "Existing key '%s' has created_by='%s', refusing to claim as operator-managed"
            % (kid, created_by)
        )

    if not created_by:
        if not isinstance(existing_key.metadata, dict):
            existing_key.metadata = {}
        existing_key.metadata["created_by"] = OPERATOR_MANAGED_CREATED_BY
        existing_key.save()
        logger.info("Backfilled created_by metadata on existing key '%s'", kid)


def _import_service_key_from_files():
    """
    Imports a service key from operator-mounted files. Used in normal (non-readonly) mode
    when INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES is true.
    """
    kid, private_key, public_jwk = _load_mounted_key_material()

    service = app.config["INSTANCE_SERVICE_KEY_SERVICE"]
    minutes_until_expiration = app.config.get("INSTANCE_SERVICE_KEY_EXPIRATION", 120)
    expiration = datetime.utcnow() + timedelta(minutes=minutes_until_expiration)

    # Direct lookup by kid before any path that triggers _gc_expired().
    try:
        existing_key = ServiceKey.select().where(ServiceKey.kid == kid).get()
    except ServiceKey.DoesNotExist:
        existing_key = None

    if existing_key is not None:
        _validate_existing_key(existing_key, kid, public_jwk, service)
        ServiceKey.update(expiration_date=expiration).where(ServiceKey.kid == kid).execute()
        logger.info("Refreshed expiration for existing operator-managed key '%s'", kid)
    else:
        try:
            create_service_key(
                "operator-managed-readonly",
                kid,
                service,
                public_jwk,
                {"created_by": OPERATOR_MANAGED_CREATED_BY},
                expiration,
            )
            logger.info("Created operator-managed service key '%s'", kid)
        except IntegrityError:
            # Concurrent pod raced to create the same key.
            try:
                existing_key = ServiceKey.select().where(ServiceKey.kid == kid).get()
            except ServiceKey.DoesNotExist:
                raise Exception(
                    "IntegrityError creating key '%s' but row not found on re-read" % kid
                )
            _validate_existing_key(existing_key, kid, public_jwk, service)
            ServiceKey.update(expiration_date=expiration).where(ServiceKey.kid == kid).execute()
            logger.info("Adopted key '%s' created by concurrent pod", kid)

    # Auto-approve if not already approved.
    try:
        existing_key = ServiceKey.select().where(ServiceKey.kid == kid).get()
    except ServiceKey.DoesNotExist:
        raise Exception("Key '%s' disappeared after import" % kid)

    if existing_key.approval is None:
        try:
            approve_service_key(kid, ServiceKeyApprovalType.AUTOMATIC)
            logger.info("Auto-approved operator-managed key '%s'", kid)
        except ServiceKeyAlreadyApproved:
            logger.info("Key '%s' already approved by concurrent pod", kid)

    return kid


def _verify_service_key():
    """
    Verifies the instance service key during readonly boot.
    Returns the kid on success, None on failure.
    """
    try:
        kid, _pem_data, public_jwk = _load_mounted_key_material()
    except Exception:
        logger.exception("Failed to load or validate the mounted service key material")
        return None

    service = app.config["INSTANCE_SERVICE_KEY_SERVICE"]

    try:
        key = get_service_key(kid, service=service, approved_only=True, alive_only=True)
    except ServiceKeyDoesNotExist:
        logger.error("No approved, alive service key '%s' found for service '%s'", kid, service)
        return None

    if not _jwk_matches(key.jwk, public_jwk):
        logger.error("PEM-derived JWK does not match DB JWK for key '%s'", kid)
        return None

    return kid


def _verify_legacy_service_key():
    """
    Preserves manual readonly behavior when mounted key import is not enabled.
    """
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

    except IOError:
        logger.exception("Could not load existing service key; creating a new one")
        return None


def setup_instance_service_key():
    """
    Creates or imports a service key for quay.
    """
    if app.config.get("REGISTRY_STATE", "normal") == "readonly":
        if app.config.get("INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES", False):
            quay_key_id = _verify_service_key()
        else:
            quay_key_id = _verify_legacy_service_key()
        if quay_key_id is None:
            raise Exception("No valid service key found for read-only registry.")
        return

    if app.config.get("INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES", False):
        kid_path = app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"]
        pem_path = app.config["INSTANCE_SERVICE_KEY_LOCATION"]
        if not os.path.exists(kid_path) or not os.path.exists(pem_path):
            raise Exception(
                "INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES is true but key files are missing: "
                "%s, %s" % (kid_path, pem_path)
            )
        _import_service_key_from_files()
        return

    # Default: generate the key for this Quay instance.
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

    try:
        with db_transaction():
            lock_bootstrap_token_operation()

            bootstrap_application, stale_applications = (
                get_singleton_bootstrap_application_candidates(owner)
            )
            if bootstrap_application is not None:
                if stale_applications:
                    delete_applications(stale_applications)
                    logger.info(
                        "Deleted %s stale bootstrap applications",
                        len(stale_applications),
                    )

                # Treat the database as the startup source of truth for Phase 1 local
                # host-file storage in standalone installations. In multi-node setups
                # using node-local files, this host may legitimately not have the file
                # that another host wrote. The plaintext token cannot be reconstructed
                # from the DB, so do not rotate or recreate it solely because the local
                # file is missing or malformed.
                logger.info("Bootstrap token already provisioned, skipping")
                return

            bootstrap_application = create_bootstrap_application(get_bootstrap_app_name(), owner)
            _, access_token = create_bootstrap_oauth_api_token(
                bootstrap_application,
                owner,
                scope,
                expiration_seconds=expiration,
            )
            if stale_applications:
                delete_applications(stale_applications)
                logger.info(
                    "Deleted %s stale bootstrap applications",
                    len(stale_applications),
                )
            write_bootstrap_token(app.config, access_token)
            logger.info("Bootstrap token provisioned")
            return
    except OSError:
        logger.exception("Failed to write bootstrap token, rolled back")
        return


def _revoke_bootstrap_tokens():
    with db_transaction():
        lock_bootstrap_token_operation()

        # Cleanup intentionally ignores the current owner config. Bootstrap credentials
        # created under a previous owner remain valid until deleted or expired.
        bootstrap_applications = get_bootstrap_managed_applications()

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

    readonly = app.config.get("REGISTRY_STATE") == "readonly"

    if not readonly:
        sync_database_with_config(app.config)
    else:
        logger.debug("Registry is in read-only mode, skipping config-to-database sync")

    setup_instance_service_key()
    setup_bootstrap_token()

    if not readonly and release.REGION and release.GIT_HEAD:
        set_region_release(release.SERVICE, release.REGION, release.GIT_HEAD)


if __name__ == "__main__":
    main()
