"""
Tests for config validation framework.
"""

import pytest

from util.config.validation import (
    ValidationError,
    validate_config,
    validate_config_or_raise,
)
from util.config.validation.fieldgroups import (
    validate_accesssettings,
    validate_database,
    validate_distributedstorage,
    validate_email,
    validate_hostsettings,
    validate_redis,
    validate_repomirror,
    validate_securityscanner,
    validate_timemachine,
)
from util.config.validation.validators import (
    validate_at_least_one_of_bool,
    validate_at_least_one_of_string,
    validate_is_email,
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


class TestValidators:
    """Tests for shared validator functions."""

    def test_validate_required_string_missing(self):
        err = validate_required_string(None, "FIELD", "TestGroup")
        assert err is not None
        assert err.field_group == "TestGroup"
        assert err.tags == ["FIELD"]
        assert "is required" in err.message

    def test_validate_required_string_empty(self):
        err = validate_required_string("", "FIELD", "TestGroup")
        assert err is not None

    def test_validate_required_string_valid(self):
        err = validate_required_string("value", "FIELD", "TestGroup")
        assert err is None

    def test_validate_is_hostname_valid(self):
        assert validate_is_hostname("quay.io", "H", "G") is None
        assert validate_is_hostname("quay.io:443", "H", "G") is None
        assert validate_is_hostname("localhost", "H", "G") is None
        assert validate_is_hostname("my-host.example.com", "H", "G") is None

    def test_validate_is_hostname_invalid(self):
        err = validate_is_hostname("http://quay.io", "H", "G")
        assert err is not None
        assert "Hostname" in err.message

    def test_validate_is_url_valid(self):
        assert validate_is_url("https://quay.io", "U", "G") is None
        assert validate_is_url("http://localhost:8080/path", "U", "G") is None

    def test_validate_is_url_invalid(self):
        err = validate_is_url("not-a-url", "U", "G")
        assert err is not None

    def test_validate_is_one_of_valid(self):
        assert validate_is_one_of("http", ["http", "https"], "F", "G") is None

    def test_validate_is_one_of_invalid(self):
        err = validate_is_one_of("ftp", ["http", "https"], "F", "G")
        assert err is not None
        assert "must be one of" in err.message

    def test_validate_time_pattern_valid(self):
        assert validate_time_pattern("2w", "F", "G") is None
        assert validate_time_pattern("30d", "F", "G") is None
        assert validate_time_pattern("1h", "F", "G") is None
        assert validate_time_pattern("0s", "F", "G") is None

    def test_validate_time_pattern_invalid(self):
        err = validate_time_pattern("2weeks", "F", "G")
        assert err is not None

    # validate_required_object tests
    def test_validate_required_object_missing(self):
        err = validate_required_object(None, "FIELD", "TestGroup")
        assert err is not None
        assert "is required" in err.message

    def test_validate_required_object_not_dict(self):
        err = validate_required_object("not a dict", "FIELD", "TestGroup")
        assert err is not None

    def test_validate_required_object_valid(self):
        err = validate_required_object({"key": "value"}, "FIELD", "TestGroup")
        assert err is None

    # validate_at_least_one_of_string tests
    def test_validate_at_least_one_of_string_none_present(self):
        err = validate_at_least_one_of_string([None, "", None], ["A", "B", "C"], "G")
        assert err is not None
        assert "At least one of" in err.message

    def test_validate_at_least_one_of_string_one_present(self):
        err = validate_at_least_one_of_string([None, "value", None], ["A", "B", "C"], "G")
        assert err is None

    # validate_at_least_one_of_bool tests
    def test_validate_at_least_one_of_bool_none_true(self):
        err = validate_at_least_one_of_bool([False, False], ["A", "B"], "G")
        assert err is not None
        assert "must be enabled" in err.message

    def test_validate_at_least_one_of_bool_one_true(self):
        err = validate_at_least_one_of_bool([False, True], ["A", "B"], "G")
        assert err is None

    # validate_is_type tests
    def test_validate_is_type_correct(self):
        assert validate_is_type(True, bool, "F", "G") is None
        assert validate_is_type("string", str, "F", "G") is None
        assert validate_is_type(123, int, "F", "G") is None

    def test_validate_is_type_incorrect(self):
        err = validate_is_type("not a bool", bool, "F", "G")
        assert err is not None
        assert "must be of type bool" in err.message

    def test_validate_is_type_none(self):
        assert validate_is_type(None, bool, "F", "G") is None

    # validate_port tests
    def test_validate_port_valid(self):
        assert validate_port(80, "F", "G") is None
        assert validate_port(443, "F", "G") is None
        assert validate_port(6379, "F", "G") is None
        assert validate_port(65535, "F", "G") is None

    def test_validate_port_invalid_type(self):
        err = validate_port("80", "F", "G")
        assert err is not None
        assert "port number" in err.message

    def test_validate_port_out_of_range(self):
        err = validate_port(0, "F", "G")
        assert err is not None
        err = validate_port(70000, "F", "G")
        assert err is not None

    def test_validate_port_none(self):
        assert validate_port(None, "F", "G") is None

    # validate_is_positive_int tests
    def test_validate_is_positive_int_valid(self):
        assert validate_is_positive_int(0, "F", "G") is None
        assert validate_is_positive_int(100, "F", "G") is None

    def test_validate_is_positive_int_negative(self):
        err = validate_is_positive_int(-1, "F", "G")
        assert err is not None
        assert "positive integer" in err.message

    def test_validate_is_positive_int_not_int(self):
        err = validate_is_positive_int("5", "F", "G")
        assert err is not None

    # validate_is_list tests
    def test_validate_is_list_valid(self):
        assert validate_is_list([], "F", "G") is None
        assert validate_is_list([1, 2, 3], "F", "G") is None

    def test_validate_is_list_invalid(self):
        err = validate_is_list("not a list", "F", "G")
        assert err is not None
        assert "must be a list" in err.message

    def test_validate_is_list_none(self):
        assert validate_is_list(None, "F", "G") is None

    # validate_is_email tests
    def test_validate_is_email_valid(self):
        assert validate_is_email("user@example.com", "F", "G") is None
        assert validate_is_email("test.user@domain.org", "F", "G") is None

    def test_validate_is_email_invalid(self):
        err = validate_is_email("not-an-email", "F", "G")
        assert err is not None
        assert "valid email" in err.message

    def test_validate_is_email_empty(self):
        assert validate_is_email("", "F", "G") is None
        assert validate_is_email(None, "F", "G") is None


class TestFieldGroupValidators:
    """Tests for field group validators."""

    def test_validate_database_missing_uri(self):
        errors = validate_database({})
        assert len(errors) == 1
        assert errors[0].tags == ["DB_URI"]

    def test_validate_database_valid(self):
        errors = validate_database({"DB_URI": "postgresql://localhost/quay"})
        assert len(errors) == 0

    def test_validate_database_invalid_sslmode(self):
        errors = validate_database(
            {
                "DB_URI": "postgresql://localhost/quay",
                "DB_CONNECTION_ARGS": {"sslmode": "invalid"},
            }
        )
        assert len(errors) == 1
        assert "sslmode" in errors[0].tags[0]

    def test_validate_hostsettings_missing_hostname(self):
        errors = validate_hostsettings({})
        assert len(errors) == 1
        assert errors[0].tags == ["SERVER_HOSTNAME"]

    def test_validate_hostsettings_valid(self):
        errors = validate_hostsettings(
            {
                "SERVER_HOSTNAME": "quay.example.com",
                "PREFERRED_URL_SCHEME": "https",
            }
        )
        assert len(errors) == 0

    def test_validate_hostsettings_invalid_scheme(self):
        errors = validate_hostsettings(
            {
                "SERVER_HOSTNAME": "quay.example.com",
                "PREFERRED_URL_SCHEME": "ftp",
            }
        )
        assert len(errors) == 1
        assert "PREFERRED_URL_SCHEME" in errors[0].tags

    def test_validate_redis_missing_required(self):
        errors = validate_redis({})
        assert len(errors) == 2  # BUILDLOGS_REDIS and USER_EVENTS_REDIS

    def test_validate_redis_valid(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"host": "redis.example.com"},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            }
        )
        assert len(errors) == 0

    def test_validate_redis_missing_host(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"port": 6379},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            }
        )
        assert len(errors) == 1
        assert "BUILDLOGS_REDIS.host" in errors[0].tags[0]

    # Edge case tests for existing validators
    def test_validate_database_connection_args_not_dict(self):
        errors = validate_database(
            {
                "DB_URI": "postgresql://localhost/quay",
                "DB_CONNECTION_ARGS": "not a dict",
            }
        )
        assert len(errors) == 1
        assert "must be an object" in errors[0].message

    def test_validate_redis_pull_metrics_not_dict(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"host": "redis.example.com"},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
                "PULL_METRICS_REDIS": "not a dict",
            }
        )
        assert len(errors) == 1
        assert "PULL_METRICS_REDIS" in errors[0].tags[0]
        assert "must be an object" in errors[0].message

    def test_validate_redis_invalid_port(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"host": "redis.example.com", "port": "invalid"},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            }
        )
        assert len(errors) == 1
        assert "port" in errors[0].tags[0]

    def test_validate_redis_invalid_password_type(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"host": "redis.example.com", "password": 12345},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            }
        )
        assert len(errors) == 1
        assert "password" in errors[0].tags[0]

    def test_validate_redis_invalid_ssl_type(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"host": "redis.example.com", "ssl": "yes"},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            }
        )
        assert len(errors) == 1
        assert "ssl" in errors[0].tags[0]

    def test_validate_hostsettings_invalid_tls_type(self):
        errors = validate_hostsettings(
            {
                "SERVER_HOSTNAME": "quay.example.com",
                "EXTERNAL_TLS_TERMINATION": "yes",
            }
        )
        assert len(errors) == 1
        assert "EXTERNAL_TLS_TERMINATION" in errors[0].tags[0]

    def test_validate_hostsettings_invalid_hostname_format(self):
        errors = validate_hostsettings({"SERVER_HOSTNAME": "http://invalid"})
        assert len(errors) == 1
        assert "Hostname" in errors[0].message

    def test_validate_redis_pull_metrics_valid(self):
        errors = validate_redis(
            {
                "BUILDLOGS_REDIS": {"host": "redis.example.com"},
                "USER_EVENTS_REDIS": {"host": "redis.example.com"},
                "PULL_METRICS_REDIS": {"host": "metrics-redis.example.com", "port": 6380},
            }
        )
        assert len(errors) == 0


class TestValidateConfig:
    """Tests for the main validate_config entry point."""

    def test_valid_minimal_config(self):
        config = {
            "SERVER_HOSTNAME": "quay.example.com",
            "DB_URI": "postgresql://localhost/quay",
            "BUILDLOGS_REDIS": {"host": "redis.example.com"},
            "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            "DISTRIBUTED_STORAGE_CONFIG": {
                "default": ["LocalStorage", {"storage_path": "/storage"}],
            },
            "DISTRIBUTED_STORAGE_PREFERENCE": ["default"],
        }
        errors = validate_config(config)
        assert len(errors) == 0

    def test_multiple_validation_errors(self):
        config = {}
        errors = validate_config(config)
        # Should have errors from multiple field groups
        field_groups = set(e.field_group for e in errors)
        assert len(field_groups) > 1

    def test_validate_config_or_raise_valid(self):
        config = {
            "SERVER_HOSTNAME": "quay.example.com",
            "DB_URI": "postgresql://localhost/quay",
            "BUILDLOGS_REDIS": {"host": "redis.example.com"},
            "USER_EVENTS_REDIS": {"host": "redis.example.com"},
            "DISTRIBUTED_STORAGE_CONFIG": {
                "default": ["LocalStorage", {"storage_path": "/storage"}],
            },
            "DISTRIBUTED_STORAGE_PREFERENCE": ["default"],
        }
        # Should not raise
        validate_config_or_raise(config)

    def test_validate_config_or_raise_invalid(self):
        with pytest.raises(ValueError) as exc_info:
            validate_config_or_raise({})
        assert "Configuration validation failed" in str(exc_info.value)


class TestDistributedStorageValidator:
    """Tests for validate_distributedstorage."""

    def test_validate_distributedstorage_missing_config(self):
        errors = validate_distributedstorage({})
        assert len(errors) == 1
        assert "DISTRIBUTED_STORAGE_CONFIG" in errors[0].tags[0]

    def test_validate_distributedstorage_missing_preference(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["LocalStorage", {"storage_path": "/storage"}],
                },
            }
        )
        assert len(errors) == 1
        assert "DISTRIBUTED_STORAGE_PREFERENCE" in errors[0].tags[0]

    def test_validate_distributedstorage_preference_not_list(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["LocalStorage", {"storage_path": "/storage"}],
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": "default",
            }
        )
        assert len(errors) == 1
        assert "must be a list" in errors[0].message

    def test_validate_distributedstorage_preference_empty(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["LocalStorage", {"storage_path": "/storage"}],
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": [],
            }
        )
        assert len(errors) == 1
        assert "at least one" in errors[0].message

    def test_validate_distributedstorage_preference_not_in_config(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["LocalStorage", {"storage_path": "/storage"}],
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": ["nonexistent"],
            }
        )
        assert len(errors) == 1
        assert "not found" in errors[0].message

    def test_validate_distributedstorage_invalid_engine_config(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": "not a list",
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": ["default"],
            }
        )
        assert len(errors) == 1
        assert "must be a list" in errors[0].message

    def test_validate_distributedstorage_engine_config_too_short(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["LocalStorage"],
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": ["default"],
            }
        )
        assert len(errors) == 1
        assert "must be a list with" in errors[0].message

    def test_validate_distributedstorage_unknown_engine_type(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["UnknownStorage", {}],
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": ["default"],
            }
        )
        assert len(errors) == 1
        assert "Unknown storage engine" in errors[0].message

    def test_validate_distributedstorage_valid(self):
        errors = validate_distributedstorage(
            {
                "DISTRIBUTED_STORAGE_CONFIG": {
                    "default": ["LocalStorage", {"storage_path": "/storage"}],
                    "s3": ["S3Storage", {"bucket": "my-bucket"}],
                },
                "DISTRIBUTED_STORAGE_PREFERENCE": ["default", "s3"],
            }
        )
        assert len(errors) == 0


class TestAccessSettingsValidator:
    """Tests for validate_accesssettings."""

    def test_validate_accesssettings_valid_auth_type(self):
        errors = validate_accesssettings({"AUTHENTICATION_TYPE": "Database"})
        assert len(errors) == 0

    def test_validate_accesssettings_invalid_auth_type(self):
        errors = validate_accesssettings({"AUTHENTICATION_TYPE": "InvalidType"})
        assert len(errors) == 1
        assert "must be one of" in errors[0].message

    def test_validate_accesssettings_feature_flag_invalid_type(self):
        errors = validate_accesssettings({"FEATURE_DIRECT_LOGIN": "not a bool"})
        assert len(errors) == 1
        assert "must be of type bool" in errors[0].message

    def test_validate_accesssettings_multiple_feature_flags(self):
        errors = validate_accesssettings(
            {
                "FEATURE_DIRECT_LOGIN": True,
                "FEATURE_GITHUB_LOGIN": False,
                "FEATURE_USER_CREATION": True,
            }
        )
        assert len(errors) == 0


class TestTimeMachineValidator:
    """Tests for validate_timemachine."""

    def test_validate_timemachine_valid(self):
        errors = validate_timemachine(
            {
                "DEFAULT_TAG_EXPIRATION": "2w",
                "TAG_EXPIRATION_OPTIONS": ["1d", "1w", "2w", "4w"],
            }
        )
        assert len(errors) == 0

    def test_validate_timemachine_invalid_default_pattern(self):
        errors = validate_timemachine({"DEFAULT_TAG_EXPIRATION": "invalid"})
        assert len(errors) == 1
        assert "regex pattern" in errors[0].message

    def test_validate_timemachine_options_not_list(self):
        errors = validate_timemachine({"TAG_EXPIRATION_OPTIONS": "not a list"})
        assert len(errors) == 1
        assert "must be a list" in errors[0].message

    def test_validate_timemachine_invalid_option_pattern(self):
        errors = validate_timemachine({"TAG_EXPIRATION_OPTIONS": ["1d", "invalid"]})
        assert len(errors) == 1
        assert "TAG_EXPIRATION_OPTIONS[1]" in errors[0].tags[0]

    def test_validate_timemachine_default_not_in_options(self):
        errors = validate_timemachine(
            {
                "DEFAULT_TAG_EXPIRATION": "3w",
                "TAG_EXPIRATION_OPTIONS": ["1d", "1w", "2w"],
            }
        )
        assert len(errors) == 1
        assert "must be one of TAG_EXPIRATION_OPTIONS" in errors[0].message


class TestEmailValidator:
    """Tests for validate_email."""

    def test_validate_email_disabled(self):
        errors = validate_email({"FEATURE_MAILING": False})
        assert len(errors) == 0

    def test_validate_email_not_configured(self):
        errors = validate_email({})
        assert len(errors) == 0

    def test_validate_email_enabled_missing_server(self):
        errors = validate_email({"FEATURE_MAILING": True})
        assert len(errors) == 1
        assert "MAIL_SERVER" in errors[0].tags[0]

    def test_validate_email_invalid_port(self):
        errors = validate_email(
            {
                "FEATURE_MAILING": True,
                "MAIL_SERVER": "smtp.example.com",
                "MAIL_PORT": "not an int",
            }
        )
        assert len(errors) == 1
        assert "port number" in errors[0].message

    def test_validate_email_invalid_tls_type(self):
        errors = validate_email(
            {
                "FEATURE_MAILING": True,
                "MAIL_SERVER": "smtp.example.com",
                "MAIL_USE_TLS": "yes",
            }
        )
        assert len(errors) == 1
        assert "must be of type bool" in errors[0].message

    def test_validate_email_auth_missing_credentials(self):
        errors = validate_email(
            {
                "FEATURE_MAILING": True,
                "MAIL_SERVER": "smtp.example.com",
                "MAIL_USE_AUTH": True,
            }
        )
        assert len(errors) == 2
        tags = [e.tags[0] for e in errors]
        assert "MAIL_USERNAME" in tags
        assert "MAIL_PASSWORD" in tags

    def test_validate_email_valid(self):
        errors = validate_email(
            {
                "FEATURE_MAILING": True,
                "MAIL_SERVER": "smtp.example.com",
                "MAIL_PORT": 587,
                "MAIL_USE_TLS": True,
                "MAIL_USE_AUTH": True,
                "MAIL_USERNAME": "user",
                "MAIL_PASSWORD": "pass",
            }
        )
        assert len(errors) == 0


class TestSecurityScannerValidator:
    """Tests for validate_securityscanner."""

    def test_validate_securityscanner_disabled(self):
        errors = validate_securityscanner({"FEATURE_SECURITY_SCANNER": False})
        assert len(errors) == 0

    def test_validate_securityscanner_not_configured(self):
        errors = validate_securityscanner({})
        assert len(errors) == 0

    def test_validate_securityscanner_enabled_missing_endpoint(self):
        errors = validate_securityscanner({"FEATURE_SECURITY_SCANNER": True})
        assert len(errors) == 1
        assert "SECURITY_SCANNER_V4_ENDPOINT" in errors[0].tags[0]

    def test_validate_securityscanner_invalid_url(self):
        errors = validate_securityscanner(
            {
                "FEATURE_SECURITY_SCANNER": True,
                "SECURITY_SCANNER_V4_ENDPOINT": "not-a-url",
            }
        )
        assert len(errors) == 1
        assert "URL" in errors[0].message

    def test_validate_securityscanner_valid(self):
        errors = validate_securityscanner(
            {
                "FEATURE_SECURITY_SCANNER": True,
                "SECURITY_SCANNER_V4_ENDPOINT": "https://clair.example.com",
            }
        )
        assert len(errors) == 0


class TestRepoMirrorValidator:
    """Tests for validate_repomirror."""

    def test_validate_repomirror_disabled(self):
        errors = validate_repomirror({"FEATURE_REPO_MIRROR": False})
        assert len(errors) == 0

    def test_validate_repomirror_not_configured(self):
        errors = validate_repomirror({})
        assert len(errors) == 0

    def test_validate_repomirror_invalid_tls_verify_type(self):
        errors = validate_repomirror(
            {
                "FEATURE_REPO_MIRROR": True,
                "REPO_MIRROR_TLS_VERIFY": "yes",
            }
        )
        assert len(errors) == 1
        assert "must be of type bool" in errors[0].message

    def test_validate_repomirror_invalid_hostname(self):
        errors = validate_repomirror(
            {
                "FEATURE_REPO_MIRROR": True,
                "REPO_MIRROR_SERVER_HOSTNAME": "http://invalid",
            }
        )
        assert len(errors) == 1
        assert "Hostname" in errors[0].message

    def test_validate_repomirror_valid(self):
        errors = validate_repomirror(
            {
                "FEATURE_REPO_MIRROR": True,
                "REPO_MIRROR_TLS_VERIFY": True,
                "REPO_MIRROR_SERVER_HOSTNAME": "mirror.example.com",
            }
        )
        assert len(errors) == 0
