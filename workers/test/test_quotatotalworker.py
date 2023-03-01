from unittest.mock import MagicMock, patch
from data.model.organization import create_organization
from data.model.user import get_user
from data.registry_model.quota import increment_namespacesize
from test.fixtures import *
from workers.quotatotalworker import QuotaTotalWorker

ORG_NAME = "orgdoesnotexist"


def test_namespace_discovery(initialized_db):
    user = get_user("devtable")
    orgdoesnotexist = create_organization("orgdoesnotexist", "orgdoesnotexist@devtable.com", user)
    orgbackfillreset = create_organization(
        "orgbackfillreset", "orgbackfillreset@devtable.com", user
    )
    increment_namespacesize(
        orgbackfillreset.id,
        0,
        "add",
        False,
        {"backfill_start_ms": None, "backfill_complete": False},
    )
    orgalreadycounted = create_organization(
        "orgalreadycounted", "orgalreadycounted@devtable.com", user
    )
    increment_namespacesize(
        orgalreadycounted.id, 0, "add", False, {"backfill_start_ms": 0, "backfill_complete": True}
    )
    expected_calls = [orgdoesnotexist.id, orgbackfillreset.id]
    with patch("workers.quotatotalworker.run_backfill", MagicMock()) as mock_run_backfill:

        def assert_mock_run_backfill(namespace_id):
            assert namespace_id != orgalreadycounted.id
            if namespace_id in expected_calls:
                expected_calls.remove(namespace_id)

        mock_run_backfill.side_effect = assert_mock_run_backfill
        worker = QuotaTotalWorker()
        worker.backfill()
        assert len(expected_calls) == 0
