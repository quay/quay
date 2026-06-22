import pytest
from jsonschema import ValidationError, validate

from config import DefaultConfig
from util.config.schema import CONFIG_SCHEMA, INTERNAL_ONLY_PROPERTIES


def test_ensure_schema_defines_all_fields():
    for key in vars(DefaultConfig):
        has_key = key in CONFIG_SCHEMA["properties"] or key in INTERNAL_ONLY_PROPERTIES
        assert has_key, "Property `%s` is missing from config schema" % key


def test_programmatic_token_expiration_must_be_positive():
    schema = CONFIG_SCHEMA["properties"]["PROGRAMMATIC_TOKEN_EXPIRATION"]

    validate(1, schema)

    for value in [0, -1]:
        with pytest.raises(ValidationError):
            validate(value, schema)
