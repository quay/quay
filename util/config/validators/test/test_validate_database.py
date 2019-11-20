import pytest

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_database import DatabaseValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config,user,user_password,expected",
    [
        (ValidatorContext(None), None, None, TypeError),
        (ValidatorContext({}), None, None, KeyError),
        (ValidatorContext({"DB_URI": "sqlite:///:memory:"}), None, None, None),
        (ValidatorContext({"DB_URI": "invalid:///:memory:"}), None, None, KeyError),
        (ValidatorContext({"DB_NOTURI": "sqlite:///:memory:"}), None, None, KeyError),
    ],
)
def test_validate_database(unvalidated_config, user, user_password, expected, app):
    validator = DatabaseValidator()

    if expected is not None:
        with pytest.raises(expected):
            validator.validate(unvalidated_config)
    else:
        validator.validate(unvalidated_config)
