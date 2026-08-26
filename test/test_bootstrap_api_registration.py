from config import DefaultConfig
from test.fixtures import *
from test.testconfig import TestConfig


def test_programmatic_bootstrap_disabled_by_default():
    assert DefaultConfig.FEATURE_PROGRAMMATIC_BOOTSTRAP is False


def test_pytest_config_registers_bootstrap_renew_route(app):
    assert TestConfig.FEATURE_PROGRAMMATIC_BOOTSTRAP is True
    assert any(rule.rule == "/api/v1/bootstrap/renew" for rule in app.url_map.iter_rules())


def test_pytest_config_bootstrap_token_path_uses_unique_db_filename():
    assert TestConfig.BOOTSTRAP_TOKEN_PATH == f"{TestConfig.TEST_DB_FILE.name}-bootstrap-token.json"
