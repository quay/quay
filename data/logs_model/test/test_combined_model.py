from datetime import date, datetime, timedelta

from freezegun import freeze_time

from data.logs_model.inmemory_model import InMemoryModel
from data.logs_model.combined_model import CombinedLogsModel

from test.fixtures import *


@pytest.fixture()
def first_model():
    return InMemoryModel()


@pytest.fixture()
def second_model():
    return InMemoryModel()


@pytest.fixture()
def combined_model(first_model, second_model, initialized_db):
    return CombinedLogsModel(first_model, second_model)


def test_log_action(first_model, second_model, combined_model, initialized_db):
    day = date(2019, 1, 1)

    # Write to the combined model.
    with freeze_time(day):
        combined_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

    simple_repo = model.repository.get_repository("devtable", "simple")

    # Make sure it is found in the first model but not the second.
    assert combined_model.count_repository_actions(simple_repo, day) == 1
    assert first_model.count_repository_actions(simple_repo, day) == 1
    assert second_model.count_repository_actions(simple_repo, day) == 0


def test_count_repository_actions(first_model, second_model, combined_model, initialized_db):
    today = date(2019, 1, 1)

    # Write to the combined model.
    with freeze_time(today):
        # Write to each model.
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

        second_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        second_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

        # Ensure the counts match as expected.
        simple_repo = model.repository.get_repository("devtable", "simple")

        assert first_model.count_repository_actions(simple_repo, today) == 3
        assert second_model.count_repository_actions(simple_repo, today) == 2
        assert combined_model.count_repository_actions(simple_repo, today) == 5


def test_yield_logs_for_export(first_model, second_model, combined_model, initialized_db):
    now = datetime.now()

    with freeze_time(now):
        # Write to each model.
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

        second_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        second_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

    later = now + timedelta(minutes=60)

    # Ensure the full set of logs is yielded.
    first_logs = list(first_model.yield_logs_for_export(now, later))[0]
    second_logs = list(second_model.yield_logs_for_export(now, later))[0]

    combined = list(combined_model.yield_logs_for_export(now, later))
    full_combined = []
    for subset in combined:
        full_combined.extend(subset)

    assert len(full_combined) == len(first_logs) + len(second_logs)
    assert full_combined == (first_logs + second_logs)


def test_lookup_logs(first_model, second_model, combined_model, initialized_db):
    now = datetime.now()

    with freeze_time(now):
        # Write to each model.
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        first_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

        second_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        second_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

    later = now + timedelta(minutes=60)

    def _collect_logs(model):
        page_token = None
        all_logs = []
        while True:
            paginated_logs = model.lookup_logs(now, later, page_token=page_token)
            page_token = paginated_logs.next_page_token
            all_logs.extend(paginated_logs.logs)
            if page_token is None:
                break
        return all_logs

    first_logs = _collect_logs(first_model)
    second_logs = _collect_logs(second_model)
    combined = _collect_logs(combined_model)

    assert len(combined) == len(first_logs) + len(second_logs)
    assert combined == (first_logs + second_logs)
