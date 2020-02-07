import pytest

from data.database import LogEntry3, User
from data.model import config as _config
from data.model.log import log_action

from mock import patch, Mock, DEFAULT, sentinel
from peewee import PeeweeException


@pytest.fixture(scope="function")
def app_config():
    with patch.dict(_config.app_config, {}, clear=True):
        yield _config.app_config


@pytest.fixture()
def logentry_kind():
    kinds = {"pull_repo": "pull_repo_kind", "push_repo": "push_repo_kind"}
    with patch("data.model.log.get_log_entry_kinds", return_value=kinds, spec=True):
        yield kinds


@pytest.fixture()
def logentry(logentry_kind):
    with patch("data.database.LogEntry3.create", spec=True):
        yield LogEntry3


@pytest.fixture()
def user():
    with patch.multiple(
        "data.database.User", username=DEFAULT, get=DEFAULT, select=DEFAULT
    ) as user:
        user["get"].return_value = Mock(id="mock_user_id")
        user["select"].return_value.tuples.return_value.get.return_value = ["default_user_id"]
        yield User


@pytest.mark.parametrize("action_kind", [("pull"), ("oops")])
def test_log_action_unknown_action(action_kind):
    """
    test unknown action types throw an exception when logged.
    """
    with pytest.raises(Exception):
        log_action(action_kind, None)


@pytest.mark.parametrize(
    "user_or_org_name,account_id,account",
    [
        ("my_test_org", "N/A", "mock_user_id"),
        (None, "test_account_id", "test_account_id"),
        (None, None, "default_user_id"),
    ],
)
@pytest.mark.parametrize(
    "unlogged_pulls_ok,action_kind,db_exception,throws",
    [
        (False, "pull_repo", None, False),
        (False, "push_repo", None, False),
        (False, "pull_repo", PeeweeException, True),
        (False, "push_repo", PeeweeException, True),
        (True, "pull_repo", PeeweeException, False),
        (True, "push_repo", PeeweeException, True),
        (True, "pull_repo", Exception, True),
        (True, "push_repo", Exception, True),
    ],
)
def test_log_action(
    user_or_org_name,
    account_id,
    account,
    unlogged_pulls_ok,
    action_kind,
    db_exception,
    throws,
    app_config,
    logentry,
    user,
):
    log_args = {
        "performer": Mock(id="TEST_PERFORMER_ID"),
        "repository": Mock(id="TEST_REPO"),
        "ip": "TEST_IP",
        "metadata": {"test_key": "test_value"},
        "timestamp": "TEST_TIMESTAMP",
    }
    app_config["SERVICE_LOG_ACCOUNT_ID"] = account_id
    app_config["ALLOW_PULLS_WITHOUT_STRICT_LOGGING"] = unlogged_pulls_ok

    logentry.create.side_effect = db_exception

    if throws:
        with pytest.raises(db_exception):
            log_action(action_kind, user_or_org_name, **log_args)
    else:
        log_action(action_kind, user_or_org_name, **log_args)

    logentry.create.assert_called_once_with(
        kind=action_kind + "_kind",
        account=account,
        performer="TEST_PERFORMER_ID",
        repository="TEST_REPO",
        ip="TEST_IP",
        metadata_json='{"test_key": "test_value"}',
        datetime="TEST_TIMESTAMP",
    )
