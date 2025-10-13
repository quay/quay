import random
import string
import time
from unittest.mock import MagicMock, patch

from app import billing as stripe
from app import marketplace_subscriptions, marketplace_users
from data import model
from test.fixtures import *
from workers.reconciliationworker import (
    ReconciliationWorker,
    reconciliation_api_call_duration,
    reconciliation_api_call_errors,
    reconciliation_api_calls,
    reconciliation_duration_seconds,
    reconciliation_last_success_timestamp,
    reconciliation_runs_total,
    reconciliation_users_not_processed,
    reconciliation_users_processed,
    reconciliation_users_total,
    track_api_call,
)

worker = ReconciliationWorker()


def test_skip_free_user(initialized_db):

    free_user = model.user.create_user("free_user", "password", "free_user@test.com")
    free_user.save()

    with patch.object(marketplace_subscriptions, "create_entitlement") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # adding the free tier
    mock.assert_called_with(23456, "MW04192")


def test_reconcile_org_user(initialized_db):
    user = model.user.get_user("devtable")

    org_user = model.organization.create_organization("org_user", "org_user@test.com", user)
    org_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    org_user.save()
    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    mock.assert_called_with(org_user.email, raise_exception=True)


def test_exception_handling(initialized_db, caplog):
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.InvalidRequestError
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.APIConnectionError
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)


def test_attribute_error(initialized_db, caplog):
    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()

    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:

        class MockCustomer:
            @property
            def subscription(self):
                raise AttributeError

        mock.return_value = MockCustomer()
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)


def test_create_for_stripe_user(initialized_db):

    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    with patch.object(marketplace_subscriptions, "create_entitlement") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # expect that entitlment is created with account number
    mock.assert_called_with(11111, "FakeSKU", raise_exception=True)


def test_empty_email(initialized_db):
    test_user = model.user.create_user("stripe_user", "password", "", email_required=False)
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()

    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    assert "" not in mock.call_args_list


def test_null_email(initialized_db):
    test_user = model.user.create_user("stripe_user", "password", None, email_required=False)
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()

    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    assert None not in mock.call_args_list


# Metrics tests


def test_track_api_call_context_manager():
    """Test that the track_api_call context manager increments metrics correctly."""
    # Get initial values
    initial_count = reconciliation_api_calls.labels(
        api="test_api", operation="test_op"
    )._value.get()

    # Use the context manager
    with track_api_call("test_api", "test_op"):
        time.sleep(0.01)  # Simulate some work

    # Check counter was incremented
    final_count = reconciliation_api_calls.labels(api="test_api", operation="test_op")._value.get()
    assert final_count == initial_count + 1

    # Check duration was recorded (histogram will have samples)
    histogram = reconciliation_api_call_duration.labels(api="test_api", operation="test_op")
    assert histogram._sum.get() > 0


def test_track_api_call_records_duration():
    """Test that API call duration is recorded correctly."""
    # Get initial duration sum
    histogram = reconciliation_api_call_duration.labels(api="duration_test", operation="sleep_op")
    initial_sum = histogram._sum.get()

    # Perform a timed operation
    with track_api_call("duration_test", "sleep_op"):
        time.sleep(0.1)

    # Duration should have increased by at least 0.1 seconds
    final_sum = histogram._sum.get()
    assert final_sum >= initial_sum + 0.1


def test_track_api_call_handles_exceptions():
    """Test that metrics are recorded even when an exception occurs."""
    initial_count = reconciliation_api_calls.labels(
        api="error_test", operation="failing_op"
    )._value.get()
    histogram = reconciliation_api_call_duration.labels(api="error_test", operation="failing_op")
    initial_sum = histogram._sum.get()

    try:
        with track_api_call("error_test", "failing_op"):
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Counter should still be incremented
    final_count = reconciliation_api_calls.labels(
        api="error_test", operation="failing_op"
    )._value.get()
    assert final_count == initial_count + 1

    # Duration should still be recorded (sum will be greater than before)
    final_sum = histogram._sum.get()
    assert final_sum > initial_sum


def test_track_api_call_increments_error_counter():
    """Test that error counter is incremented when an exception occurs."""
    initial_error_count = reconciliation_api_call_errors.labels(
        api="error_counter_test", operation="failing_op"
    )._value.get()

    try:
        with track_api_call("error_counter_test", "failing_op"):
            raise RuntimeError("Simulated API error")
    except RuntimeError:
        pass

    # Error counter should be incremented
    final_error_count = reconciliation_api_call_errors.labels(
        api="error_counter_test", operation="failing_op"
    )._value.get()
    assert final_error_count == initial_error_count + 1


def test_track_api_call_no_error_counter_on_success():
    """Test that error counter is NOT incremented when no exception occurs."""
    initial_error_count = reconciliation_api_call_errors.labels(
        api="success_test", operation="working_op"
    )._value.get()

    with track_api_call("success_test", "working_op"):
        pass  # No exception

    # Error counter should NOT be incremented
    final_error_count = reconciliation_api_call_errors.labels(
        api="success_test", operation="working_op"
    )._value.get()
    assert final_error_count == initial_error_count


def test_missing_email_metric_incremented():
    """Test that the not processed counter increments for users without emails."""
    # Create mock users with missing emails
    user_no_email = MagicMock()
    user_no_email.email = None
    user_no_email.username = "no_email_user"

    user_empty_email = MagicMock()
    user_empty_email.email = ""
    user_empty_email.username = "empty_email_user"

    # Get initial count
    initial_count = reconciliation_users_not_processed.labels(reason="missing_email")._value.get()

    # Mock get_active_users to only return our test users
    with patch.object(
        model.user, "get_active_users", return_value=[user_no_email, user_empty_email]
    ):
        with patch.object(marketplace_users, "lookup_customer_id", return_value=None):
            worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that the counter incremented by 2 (for both users)
    final_count = reconciliation_users_not_processed.labels(reason="missing_email")._value.get()
    assert final_count == initial_count + 2


def test_no_customer_ids_metric_incremented():
    """Test that the not processed counter increments for users with no customer IDs."""
    # Create mock users with valid emails
    user1 = MagicMock()
    user1.email = "user1@test.com"
    user1.username = "user1"
    user1.stripe_id = None

    user2 = MagicMock()
    user2.email = "user2@test.com"
    user2.username = "user2"
    user2.stripe_id = None

    # Get initial count
    initial_count = reconciliation_users_not_processed.labels(reason="no_customer_ids")._value.get()

    # Mock get_active_users to return our test users
    # Mock lookup_customer_id to return None (no customer IDs found)
    with patch.object(model.user, "get_active_users", return_value=[user1, user2]):
        with patch.object(marketplace_users, "lookup_customer_id", return_value=None):
            worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that the counter incremented by 2 (for both users)
    final_count = reconciliation_users_not_processed.labels(reason="no_customer_ids")._value.get()
    assert final_count == initial_count + 2


def test_api_call_metric_incremented(initialized_db):
    """Test that API call metrics are incremented during reconciliation."""
    # Create a user with email
    test_user = model.user.create_user("api_test_user", "password", "api_test@test.com")
    test_user.save()

    # Get initial count for lookup_customer_id
    initial_count = reconciliation_api_calls.labels(
        api="marketplace_user", operation="lookup_customer_id"
    )._value.get()

    # Mock get_active_users to only return our test user
    with patch.object(model.user, "get_active_users", return_value=[test_user]):
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that the metric was incremented by exactly 1 (for our one user)
    final_count = reconciliation_api_calls.labels(
        api="marketplace_user", operation="lookup_customer_id"
    )._value.get()
    assert final_count == initial_count + 1


def test_create_entitlement_metric_incremented(initialized_db):
    """Test that create_entitlement API call metric is incremented."""
    # Create a free user
    test_user = model.user.create_user("free_test_user", "password", "free_test@test.com")
    test_user.save()

    # Get initial count
    initial_count = reconciliation_api_calls.labels(
        api="marketplace_subscription", operation="create_entitlement"
    )._value.get()

    # Run reconciliation (should create free tier entitlement)
    with patch.object(model.user, "get_active_users", return_value=[test_user]):
        # Mock lookup_customer_id to return a customer ID
        with patch.object(marketplace_users, "lookup_customer_id", return_value=[23456]):
            # Mock lookup_subscription to return None (no existing entitlement)
            with patch.object(marketplace_subscriptions, "lookup_subscription", return_value=None):
                with patch.object(marketplace_subscriptions, "create_entitlement"):
                    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that the metric was incremented by 1 (one entitlement created)
    final_count = reconciliation_api_calls.labels(
        api="marketplace_subscription", operation="create_entitlement"
    )._value.get()
    assert final_count == initial_count + 1


def test_users_total_metric_set():
    """Test that the users total gauge is set to the database user count."""
    # Create mock users
    user1 = MagicMock()
    user1.email = "user1@test.com"
    user1.username = "user1"
    user1.stripe_id = None

    user2 = MagicMock()
    user2.email = "user2@test.com"
    user2.username = "user2"
    user2.stripe_id = None

    user_no_email = MagicMock()
    user_no_email.email = None
    user_no_email.username = "user_no_email"

    # Run reconciliation with our 3 test users
    with patch.object(model.user, "get_active_users", return_value=[user1, user2, user_no_email]):
        with patch.object(marketplace_users, "lookup_customer_id", return_value=[23456]):
            with patch.object(marketplace_subscriptions, "lookup_subscription", return_value=None):
                with patch.object(marketplace_subscriptions, "create_entitlement"):
                    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that the gauge is set to 3 (DB user count)
    final_count = reconciliation_users_total._value.get()
    assert final_count == 3


def test_users_processed_metric_incremented():
    """Test that the users processed counter increments for successfully processed users."""
    # Create mock users
    user1 = MagicMock()
    user1.email = "user1@test.com"
    user1.username = "user1"
    user1.stripe_id = None

    user2 = MagicMock()
    user2.email = "user2@test.com"
    user2.username = "user2"
    user2.stripe_id = None

    # User with no email should NOT be processed
    user_no_email = MagicMock()
    user_no_email.email = None
    user_no_email.username = "user_no_email"

    # Get initial count
    initial_count = reconciliation_users_processed._value.get()

    # Run reconciliation with our 3 test users
    with patch.object(model.user, "get_active_users", return_value=[user1, user2, user_no_email]):
        with patch.object(marketplace_users, "lookup_customer_id", return_value=[23456]):
            with patch.object(marketplace_subscriptions, "lookup_subscription", return_value=None):
                with patch.object(marketplace_subscriptions, "create_entitlement"):
                    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that the counter incremented by 2 (only user1 and user2 were processed, not user_no_email)
    final_count = reconciliation_users_processed._value.get()
    assert final_count == initial_count + 2


def test_successful_reconciliation_run_metrics():
    """Test that successful reconciliation increments success metrics."""
    # Create a mock user
    user = MagicMock()
    user.email = "test@test.com"
    user.username = "test_user"
    user.stripe_id = None

    # Get initial counts
    initial_success_count = reconciliation_runs_total.labels(status="success")._value.get()
    initial_duration_sum = reconciliation_duration_seconds._sum.get()

    # Run reconciliation
    with patch.object(model.user, "get_active_users", return_value=[user]):
        with patch.object(marketplace_users, "lookup_customer_id", return_value=[23456]):
            with patch.object(marketplace_subscriptions, "lookup_subscription", return_value=None):
                with patch.object(marketplace_subscriptions, "create_entitlement"):
                    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check success counter was incremented
    final_success_count = reconciliation_runs_total.labels(status="success")._value.get()
    assert final_success_count == initial_success_count + 1

    # Check duration was recorded (sum will have increased)
    final_duration_sum = reconciliation_duration_seconds._sum.get()
    assert final_duration_sum > initial_duration_sum

    # Check last success timestamp was set
    last_success = reconciliation_last_success_timestamp._value.get()
    assert last_success > 0


def test_failed_reconciliation_run_metrics():
    """Test that failed reconciliation increments failure metrics."""
    # Get initial counts
    initial_failed_count = reconciliation_runs_total.labels(status="failed")._value.get()
    initial_duration_sum = reconciliation_duration_seconds._sum.get()

    # Force an exception during reconciliation
    with patch.object(model.user, "get_active_users", side_effect=Exception("Test failure")):
        try:
            worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)
        except Exception:
            pass  # Expected to fail

    # Check failed counter was incremented
    final_failed_count = reconciliation_runs_total.labels(status="failed")._value.get()
    assert final_failed_count == initial_failed_count + 1

    # Check duration was still recorded (in finally block - sum will have increased)
    final_duration_sum = reconciliation_duration_seconds._sum.get()
    assert final_duration_sum > initial_duration_sum


def test_reconciliation_duration_recorded():
    """Test that reconciliation duration is properly measured."""
    # Create a mock user
    user = MagicMock()
    user.email = "test@test.com"
    user.username = "test_user"
    user.stripe_id = None

    # Get initial duration sum
    initial_sum = reconciliation_duration_seconds._sum.get()

    # Run reconciliation with a small sleep to ensure measurable duration
    with patch.object(model.user, "get_active_users", return_value=[user]):
        with patch.object(marketplace_users, "lookup_customer_id", return_value=[23456]):
            with patch.object(marketplace_subscriptions, "lookup_subscription", return_value=None):
                with patch.object(marketplace_subscriptions, "create_entitlement"):
                    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # Check that duration was recorded
    final_sum = reconciliation_duration_seconds._sum.get()
    assert final_sum > initial_sum
