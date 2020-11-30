import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_actionlog_archiving import ActionLogArchivingValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
        ({"ACTION_LOG_ARCHIVE_PATH": "foo"}),
        ({"ACTION_LOG_ARCHIVE_LOCATION": ""}),
    ],
)
def test_skip_validate_actionlog(unvalidated_config, app):
    validator = ActionLogArchivingValidator()
    validator.validate(ValidatorContext(unvalidated_config))


@pytest.mark.parametrize(
    "config, expected_error",
    [
        ({"FEATURE_ACTION_LOG_ROTATION": True}, "Missing action log archive path"),
        (
            {"FEATURE_ACTION_LOG_ROTATION": True, "ACTION_LOG_ARCHIVE_PATH": ""},
            "Missing action log archive path",
        ),
        (
            {"FEATURE_ACTION_LOG_ROTATION": True, "ACTION_LOG_ARCHIVE_PATH": "foo"},
            "Missing action log archive storage location",
        ),
        (
            {
                "FEATURE_ACTION_LOG_ROTATION": True,
                "ACTION_LOG_ARCHIVE_PATH": "foo",
                "ACTION_LOG_ARCHIVE_LOCATION": "",
            },
            "Missing action log archive storage location",
        ),
        (
            {
                "FEATURE_ACTION_LOG_ROTATION": True,
                "ACTION_LOG_ARCHIVE_PATH": "foo",
                "ACTION_LOG_ARCHIVE_LOCATION": "invalid",
            },
            "Action log archive storage location `invalid` not found in storage config",
        ),
    ],
)
def test_invalid_config(config, expected_error, app):
    validator = ActionLogArchivingValidator()

    with pytest.raises(ConfigValidationException) as ipe:
        validator.validate(ValidatorContext(config))

    assert str(ipe.value) == expected_error


def test_valid_config(app):
    config = ValidatorContext(
        {
            "FEATURE_ACTION_LOG_ROTATION": True,
            "ACTION_LOG_ARCHIVE_PATH": "somepath",
            "ACTION_LOG_ARCHIVE_LOCATION": "somelocation",
            "DISTRIBUTED_STORAGE_CONFIG": {
                "somelocation": {},
            },
        }
    )

    validator = ActionLogArchivingValidator()
    validator.validate(config)
