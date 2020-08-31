import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_timemachine import TimeMachineValidator


@pytest.mark.parametrize(
    "unvalidated_config",
    [
        ({}),
    ],
)
def test_validate_noop(unvalidated_config):
    TimeMachineValidator.validate(ValidatorContext(unvalidated_config))


from test.fixtures import *


@pytest.mark.parametrize(
    "default_exp,options,expected_exception",
    [
        ("2d", ["1w", "2d"], None),
        ("2d", ["1w"], "Default expiration must be in expiration options set"),
        ("2d", ["2d", "1M"], "Invalid tag expiration option: 1M"),
    ],
)
def test_validate(default_exp, options, expected_exception, app):
    config = {}
    config["DEFAULT_TAG_EXPIRATION"] = default_exp
    config["TAG_EXPIRATION_OPTIONS"] = options

    if expected_exception is not None:
        with pytest.raises(ConfigValidationException) as cve:
            TimeMachineValidator.validate(ValidatorContext(config))
        assert str(cve.value) == str(expected_exception)
    else:
        TimeMachineValidator.validate(ValidatorContext(config))
