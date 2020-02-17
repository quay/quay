from config import DefaultConfig
from util.config.schema import CONFIG_SCHEMA, INTERNAL_ONLY_PROPERTIES


def test_ensure_schema_defines_all_fields():
    for key in vars(DefaultConfig):
        has_key = key in CONFIG_SCHEMA["properties"] or key in INTERNAL_ONLY_PROPERTIES
        assert has_key, "Property `%s` is missing from config schema" % key
