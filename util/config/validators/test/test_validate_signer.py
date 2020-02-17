import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_signer import SignerValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config,expected",
    [
        ({}, None),
        ({"SIGNING_ENGINE": "foobar"}, ConfigValidationException),
        ({"SIGNING_ENGINE": "gpg2"}, Exception),
    ],
)
def test_validate_signer(unvalidated_config, expected, app):
    validator = SignerValidator()
    if expected is not None:
        with pytest.raises(expected):
            validator.validate(ValidatorContext(unvalidated_config))
    else:
        validator.validate(ValidatorContext(unvalidated_config))
