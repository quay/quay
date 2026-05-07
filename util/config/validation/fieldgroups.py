"""
Field group validators for config validation.

Each field group validator takes a config dict and returns a list of ValidationErrors.
"""

from typing import Any, Callable, Dict, List

from .errors import ValidationError
from .validators import (
    validate_at_least_one_of_string,
    validate_is_hostname,
    validate_is_list,
    validate_is_one_of,
    validate_is_positive_int,
    validate_is_type,
    validate_is_url,
    validate_port,
    validate_required_object,
    validate_required_string,
    validate_time_pattern,
)


def validate_database(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate Database field group."""
    errors = []
    fg_name = "Database"

    # DB_URI is required
    err = validate_required_string(config.get("DB_URI"), "DB_URI", fg_name)
    if err:
        errors.append(err)

    # DB_CONNECTION_ARGS validation (optional)
    db_args = config.get("DB_CONNECTION_ARGS")
    if db_args is not None:
        if not isinstance(db_args, dict):
            errors.append(
                ValidationError(
                    field_group=fg_name,
                    tags=["DB_CONNECTION_ARGS"],
                    message="DB_CONNECTION_ARGS must be an object",
                )
            )
        else:
            # Validate sslmode if present
            sslmode = db_args.get("sslmode")
            if sslmode is not None:
                valid_sslmodes = [
                    "disable",
                    "allow",
                    "prefer",
                    "require",
                    "verify-ca",
                    "verify-full",
                ]
                err = validate_is_one_of(
                    sslmode, valid_sslmodes, "DB_CONNECTION_ARGS.sslmode", fg_name
                )
                if err:
                    errors.append(err)

    return errors


def validate_hostsettings(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate HostSettings field group."""
    errors = []
    fg_name = "HostSettings"

    # SERVER_HOSTNAME is required
    hostname = config.get("SERVER_HOSTNAME")
    err = validate_required_string(hostname, "SERVER_HOSTNAME", fg_name)
    if err:
        errors.append(err)
    else:
        err = validate_is_hostname(hostname, "SERVER_HOSTNAME", fg_name)
        if err:
            errors.append(err)

    # PREFERRED_URL_SCHEME must be http or https
    scheme = config.get("PREFERRED_URL_SCHEME")
    if scheme is not None:
        err = validate_is_one_of(scheme, ["http", "https"], "PREFERRED_URL_SCHEME", fg_name)
        if err:
            errors.append(err)

    # EXTERNAL_TLS_TERMINATION type check
    ext_tls = config.get("EXTERNAL_TLS_TERMINATION")
    if ext_tls is not None:
        err = validate_is_type(ext_tls, bool, "EXTERNAL_TLS_TERMINATION", fg_name)
        if err:
            errors.append(err)

    return errors


def _validate_redis_struct(
    redis_config: Dict[str, Any],
    field_name: str,
    fg_name: str,
) -> List[ValidationError]:
    """Validate a Redis configuration structure."""
    errors = []

    # host is required
    err = validate_required_string(
        redis_config.get("host"),
        f"{field_name}.host",
        fg_name,
    )
    if err:
        errors.append(err)

    # port validation
    port = redis_config.get("port")
    if port is not None:
        err = validate_port(port, f"{field_name}.port", fg_name)
        if err:
            errors.append(err)

    # password type check
    password = redis_config.get("password")
    if password is not None:
        err = validate_is_type(password, str, f"{field_name}.password", fg_name)
        if err:
            errors.append(err)

    # ssl type check
    ssl = redis_config.get("ssl")
    if ssl is not None:
        err = validate_is_type(ssl, bool, f"{field_name}.ssl", fg_name)
        if err:
            errors.append(err)

    return errors


def validate_redis(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate Redis field group."""
    errors = []
    fg_name = "Redis"

    # BUILDLOGS_REDIS is required
    buildlogs = config.get("BUILDLOGS_REDIS")
    err = validate_required_object(buildlogs, "BUILDLOGS_REDIS", fg_name)
    if err:
        errors.append(err)
    elif isinstance(buildlogs, dict):
        errors.extend(_validate_redis_struct(buildlogs, "BUILDLOGS_REDIS", fg_name))

    # USER_EVENTS_REDIS is required
    user_events = config.get("USER_EVENTS_REDIS")
    err = validate_required_object(user_events, "USER_EVENTS_REDIS", fg_name)
    if err:
        errors.append(err)
    elif isinstance(user_events, dict):
        errors.extend(_validate_redis_struct(user_events, "USER_EVENTS_REDIS", fg_name))

    # PULL_METRICS_REDIS is optional
    pull_metrics = config.get("PULL_METRICS_REDIS")
    if pull_metrics is not None:
        if not isinstance(pull_metrics, dict):
            errors.append(
                ValidationError(
                    field_group=fg_name,
                    tags=["PULL_METRICS_REDIS"],
                    message="PULL_METRICS_REDIS must be an object",
                )
            )
        else:
            errors.extend(_validate_redis_struct(pull_metrics, "PULL_METRICS_REDIS", fg_name))

    return errors


def validate_distributedstorage(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate DistributedStorage field group."""
    errors: List[ValidationError] = []
    fg_name = "DistributedStorage"

    # DISTRIBUTED_STORAGE_CONFIG is required
    storage_config = config.get("DISTRIBUTED_STORAGE_CONFIG")
    err = validate_required_object(storage_config, "DISTRIBUTED_STORAGE_CONFIG", fg_name)
    if err:
        errors.append(err)
        return errors

    # At this point storage_config is guaranteed to be a dict
    if not isinstance(storage_config, dict):
        return errors

    # DISTRIBUTED_STORAGE_PREFERENCE is required
    storage_pref = config.get("DISTRIBUTED_STORAGE_PREFERENCE")
    if storage_pref is None:
        errors.append(
            ValidationError(
                field_group=fg_name,
                tags=["DISTRIBUTED_STORAGE_PREFERENCE"],
                message="DISTRIBUTED_STORAGE_PREFERENCE is required",
            )
        )
    elif not isinstance(storage_pref, list):
        errors.append(
            ValidationError(
                field_group=fg_name,
                tags=["DISTRIBUTED_STORAGE_PREFERENCE"],
                message="DISTRIBUTED_STORAGE_PREFERENCE must be a list",
            )
        )
    elif len(storage_pref) == 0:
        errors.append(
            ValidationError(
                field_group=fg_name,
                tags=["DISTRIBUTED_STORAGE_PREFERENCE"],
                message="DISTRIBUTED_STORAGE_PREFERENCE must have at least one storage location",
            )
        )
    else:
        # Validate that all preferences exist in config
        for pref in storage_pref:
            if pref not in storage_config:
                errors.append(
                    ValidationError(
                        field_group=fg_name,
                        tags=["DISTRIBUTED_STORAGE_PREFERENCE"],
                        message=f"Storage location '{pref}' not found in DISTRIBUTED_STORAGE_CONFIG",
                    )
                )

    # Validate each storage engine configuration
    valid_storage_types = [
        "LocalStorage",
        "S3Storage",
        "GoogleCloudStorage",
        "AzureStorage",
        "RadosGWStorage",
        "RHOCSStorage",
        "SwiftStorage",
        "CloudFrontedS3Storage",
        "IBMCloudStorage",
        "STSS3Storage",
        "MultiCDNStorage",
    ]

    for location, engine_config in storage_config.items():
        if not isinstance(engine_config, list) or len(engine_config) < 2:
            errors.append(
                ValidationError(
                    field_group=fg_name,
                    tags=[f"DISTRIBUTED_STORAGE_CONFIG.{location}"],
                    message=f"Storage location '{location}' must be a list with [engine_type, config]",
                )
            )
            continue

        engine_type = engine_config[0]
        if engine_type not in valid_storage_types:
            errors.append(
                ValidationError(
                    field_group=fg_name,
                    tags=[f"DISTRIBUTED_STORAGE_CONFIG.{location}"],
                    message=f"Unknown storage engine type: {engine_type}",
                )
            )

    return errors


def validate_accesssettings(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate AccessSettings field group."""
    errors = []
    fg_name = "AccessSettings"

    # AUTHENTICATION_TYPE validation
    auth_type = config.get("AUTHENTICATION_TYPE")
    if auth_type is not None:
        valid_auth_types = [
            "Database",
            "LDAP",
            "JWT",
            "Keystone",
            "OIDC",
            "AppToken",
        ]
        err = validate_is_one_of(auth_type, valid_auth_types, "AUTHENTICATION_TYPE", fg_name)
        if err:
            errors.append(err)

    # Feature flags type validation
    feature_flags = [
        "FEATURE_DIRECT_LOGIN",
        "FEATURE_GITHUB_LOGIN",
        "FEATURE_GOOGLE_LOGIN",
        "FEATURE_ANONYMOUS_ACCESS",
        "FEATURE_INVITE_ONLY_USER_CREATION",
        "FEATURE_USER_CREATION",
        "FEATURE_USER_LAST_ACCESSED",
        "FEATURE_PARTIAL_USER_AUTOCOMPLETE",
        "FEATURE_REQUIRE_TEAM_INVITE",
        "FEATURE_USERNAME_CONFIRMATION",
    ]

    for flag in feature_flags:
        val = config.get(flag)
        if val is not None:
            err = validate_is_type(val, bool, flag, fg_name)
            if err:
                errors.append(err)

    return errors


def validate_timemachine(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate TimeMachine field group."""
    errors = []
    fg_name = "TimeMachine"

    # DEFAULT_TAG_EXPIRATION validation
    default_exp = config.get("DEFAULT_TAG_EXPIRATION")
    if default_exp is not None:
        err = validate_time_pattern(default_exp, "DEFAULT_TAG_EXPIRATION", fg_name)
        if err:
            errors.append(err)

    # TAG_EXPIRATION_OPTIONS validation
    exp_options = config.get("TAG_EXPIRATION_OPTIONS")
    if exp_options is not None:
        err = validate_is_list(exp_options, "TAG_EXPIRATION_OPTIONS", fg_name)
        if err:
            errors.append(err)
        else:
            for i, opt in enumerate(exp_options):
                err = validate_time_pattern(opt, f"TAG_EXPIRATION_OPTIONS[{i}]", fg_name)
                if err:
                    errors.append(err)

            # Validate that default is in options
            if default_exp and default_exp not in exp_options:
                errors.append(
                    ValidationError(
                        field_group=fg_name,
                        tags=["DEFAULT_TAG_EXPIRATION", "TAG_EXPIRATION_OPTIONS"],
                        message="DEFAULT_TAG_EXPIRATION must be one of TAG_EXPIRATION_OPTIONS",
                    )
                )

    return errors


def validate_email(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate Email field group."""
    errors: List[ValidationError] = []
    fg_name = "Email"

    # Only validate if mailing feature is enabled
    if not config.get("FEATURE_MAILING"):
        return errors

    # MAIL_SERVER is required when mailing is enabled
    mail_server = config.get("MAIL_SERVER")
    err = validate_required_string(mail_server, "MAIL_SERVER", fg_name)
    if err:
        errors.append(err)

    # MAIL_PORT validation
    mail_port = config.get("MAIL_PORT")
    if mail_port is not None:
        err = validate_port(mail_port, "MAIL_PORT", fg_name)
        if err:
            errors.append(err)

    # MAIL_USE_TLS type check
    mail_tls = config.get("MAIL_USE_TLS")
    if mail_tls is not None:
        err = validate_is_type(mail_tls, bool, "MAIL_USE_TLS", fg_name)
        if err:
            errors.append(err)

    # MAIL_USE_AUTH type check
    mail_auth = config.get("MAIL_USE_AUTH")
    if mail_auth is not None:
        err = validate_is_type(mail_auth, bool, "MAIL_USE_AUTH", fg_name)
        if err:
            errors.append(err)

    # If auth is enabled, validate username/password
    if mail_auth:
        err = validate_required_string(config.get("MAIL_USERNAME"), "MAIL_USERNAME", fg_name)
        if err:
            errors.append(err)
        err = validate_required_string(config.get("MAIL_PASSWORD"), "MAIL_PASSWORD", fg_name)
        if err:
            errors.append(err)

    return errors


def validate_securityscanner(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate SecurityScanner field group."""
    errors: List[ValidationError] = []
    fg_name = "SecurityScanner"

    # Only validate if security scanner is enabled
    if not config.get("FEATURE_SECURITY_SCANNER"):
        return errors

    # SECURITY_SCANNER_V4_ENDPOINT is required when enabled
    endpoint = config.get("SECURITY_SCANNER_V4_ENDPOINT")
    err = validate_required_string(endpoint, "SECURITY_SCANNER_V4_ENDPOINT", fg_name)
    if err:
        errors.append(err)
    else:
        err = validate_is_url(endpoint, "SECURITY_SCANNER_V4_ENDPOINT", fg_name)
        if err:
            errors.append(err)

    return errors


def validate_repomirror(config: Dict[str, Any]) -> List[ValidationError]:
    """Validate RepoMirror field group."""
    errors: List[ValidationError] = []
    fg_name = "RepoMirror"

    # Only validate if repo mirror is enabled
    if not config.get("FEATURE_REPO_MIRROR"):
        return errors

    # REPO_MIRROR_TLS_VERIFY type check
    tls_verify = config.get("REPO_MIRROR_TLS_VERIFY")
    if tls_verify is not None:
        err = validate_is_type(tls_verify, bool, "REPO_MIRROR_TLS_VERIFY", fg_name)
        if err:
            errors.append(err)

    # REPO_MIRROR_SERVER_HOSTNAME validation
    server_hostname = config.get("REPO_MIRROR_SERVER_HOSTNAME")
    if server_hostname is not None:
        err = validate_is_hostname(server_hostname, "REPO_MIRROR_SERVER_HOSTNAME", fg_name)
        if err:
            errors.append(err)

    return errors


# Registry of all field group validators
# Order matters - more fundamental validators first
FIELD_GROUP_VALIDATORS: List[Callable[[Dict[str, Any]], List[ValidationError]]] = [
    validate_hostsettings,
    validate_database,
    validate_redis,
    validate_distributedstorage,
    validate_accesssettings,
    validate_timemachine,
    validate_email,
    validate_securityscanner,
    validate_repomirror,
]
