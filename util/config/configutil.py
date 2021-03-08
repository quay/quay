from random import SystemRandom
from uuid import uuid4


def generate_secret_key():
    cryptogen = SystemRandom()
    return str(cryptogen.getrandbits(256))


def add_enterprise_config_defaults(config_obj, current_secret_key):
    """
    Adds/Sets the config defaults for enterprise registry config.
    """
    # These have to be false.
    config_obj["TESTING"] = False
    config_obj["USE_CDN"] = False

    # Defaults for Red Hat Quay.
    config_obj["REGISTRY_TITLE"] = config_obj.get("REGISTRY_TITLE", "Red Hat Quay")
    config_obj["REGISTRY_TITLE_SHORT"] = config_obj.get("REGISTRY_TITLE_SHORT", "Red Hat Quay")

    # Default features that are on.
    config_obj["FEATURE_USER_LOG_ACCESS"] = config_obj.get("FEATURE_USER_LOG_ACCESS", True)
    config_obj["FEATURE_USER_CREATION"] = config_obj.get("FEATURE_USER_CREATION", True)
    config_obj["FEATURE_ANONYMOUS_ACCESS"] = config_obj.get("FEATURE_ANONYMOUS_ACCESS", True)
    config_obj["FEATURE_REQUIRE_TEAM_INVITE"] = config_obj.get("FEATURE_REQUIRE_TEAM_INVITE", True)
    config_obj["FEATURE_CHANGE_TAG_EXPIRATION"] = config_obj.get(
        "FEATURE_CHANGE_TAG_EXPIRATION", True
    )
    config_obj["FEATURE_DIRECT_LOGIN"] = config_obj.get("FEATURE_DIRECT_LOGIN", True)
    config_obj["FEATURE_APP_SPECIFIC_TOKENS"] = config_obj.get("FEATURE_APP_SPECIFIC_TOKENS", True)
    config_obj["FEATURE_PARTIAL_USER_AUTOCOMPLETE"] = config_obj.get(
        "FEATURE_PARTIAL_USER_AUTOCOMPLETE", True
    )
    config_obj["FEATURE_USERNAME_CONFIRMATION"] = config_obj.get(
        "FEATURE_USERNAME_CONFIRMATION", True
    )
    config_obj["FEATURE_RESTRICTED_V1_PUSH"] = config_obj.get("FEATURE_RESTRICTED_V1_PUSH", True)

    # Default features that are off.
    config_obj["FEATURE_MAILING"] = config_obj.get("FEATURE_MAILING", False)
    config_obj["FEATURE_BUILD_SUPPORT"] = config_obj.get("FEATURE_BUILD_SUPPORT", False)
    config_obj["FEATURE_ACI_CONVERSION"] = config_obj.get("FEATURE_ACI_CONVERSION", False)
    config_obj["FEATURE_APP_REGISTRY"] = config_obj.get("FEATURE_APP_REGISTRY", False)
    config_obj["FEATURE_REPO_MIRROR"] = config_obj.get("FEATURE_REPO_MIRROR", False)

    # Default repo mirror config.
    config_obj["REPO_MIRROR_TLS_VERIFY"] = config_obj.get("REPO_MIRROR_TLS_VERIFY", True)
    config_obj["REPO_MIRROR_SERVER_HOSTNAME"] = config_obj.get("REPO_MIRROR_SERVER_HOSTNAME", None)

    # Default security scanner config.
    config_obj["FEATURE_SECURITY_NOTIFICATIONS"] = config_obj.get(
        "FEATURE_SECURITY_NOTIFICATIONS", True
    )

    config_obj["FEATURE_SECURITY_SCANNER"] = config_obj.get("FEATURE_SECURITY_SCANNER", False)

    config_obj["SECURITY_SCANNER_ISSUER_NAME"] = config_obj.get(
        "SECURITY_SCANNER_ISSUER_NAME", "security_scanner"
    )

    # Default time machine config.
    config_obj["TAG_EXPIRATION_OPTIONS"] = config_obj.get(
        "TAG_EXPIRATION_OPTIONS", ["0s", "1d", "1w", "2w", "4w"]
    )
    config_obj["DEFAULT_TAG_EXPIRATION"] = config_obj.get("DEFAULT_TAG_EXPIRATION", "2w")

    # Default mail setings.
    config_obj["MAIL_USE_TLS"] = config_obj.get("MAIL_USE_TLS", True)
    config_obj["MAIL_PORT"] = config_obj.get("MAIL_PORT", 587)
    config_obj["MAIL_DEFAULT_SENDER"] = config_obj.get("MAIL_DEFAULT_SENDER", "admin@example.com")

    # Default auth type.
    if not "AUTHENTICATION_TYPE" in config_obj:
        config_obj["AUTHENTICATION_TYPE"] = "Database"

    # Default secret key.
    if not "SECRET_KEY" in config_obj:
        if current_secret_key:
            config_obj["SECRET_KEY"] = current_secret_key
        else:
            config_obj["SECRET_KEY"] = generate_secret_key()

    # Default database secret key.
    if not "DATABASE_SECRET_KEY" in config_obj:
        config_obj["DATABASE_SECRET_KEY"] = generate_secret_key()

    # Default storage configuration.
    if not "DISTRIBUTED_STORAGE_CONFIG" in config_obj:
        config_obj["DISTRIBUTED_STORAGE_PREFERENCE"] = ["default"]
        config_obj["DISTRIBUTED_STORAGE_CONFIG"] = {
            "default": ["LocalStorage", {"storage_path": "/datastorage/registry"}]
        }

        config_obj["USERFILES_LOCATION"] = "default"
        config_obj["USERFILES_PATH"] = "userfiles/"

        config_obj["LOG_ARCHIVE_LOCATION"] = "default"

    # Misc configuration.
    config_obj["PREFERRED_URL_SCHEME"] = config_obj.get("PREFERRED_URL_SCHEME", "http")
    config_obj["ENTERPRISE_LOGO_URL"] = config_obj.get(
        "ENTERPRISE_LOGO_URL", "/static/img/quay-horizontal-color.svg"
    )
    config_obj["TEAM_RESYNC_STALE_TIME"] = config_obj.get("TEAM_RESYNC_STALE_TIME", "60m")
