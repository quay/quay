import logging
import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram

import features
from app import app
from app import billing as stripe
from app import marketplace_subscriptions, marketplace_users
from data import model
from data.billing import RH_SKUS, get_plan
from util.locking import GlobalLock, LockNotAcquiredException
from util.marketplace import MarketplaceApiException
from workers.gunicorn_worker import GunicornWorker
from workers.namespacegcworker import LOCK_TIMEOUT_PADDING
from workers.worker import Worker

logger = logging.getLogger(__name__)

RECONCILIATION_TIMEOUT = 5 * 60  # 5min
RECONCILIATION_FREQUENCY = 5 * 60  # run reconciliation every 5 min
MILLISECONDS_IN_SECONDS = 1000
SECONDS_IN_DAYS = 86400
ONE_MONTH = 30 * SECONDS_IN_DAYS * MILLISECONDS_IN_SECONDS
FREE_TIER_SKU = "MW04192"

# Prometheus metrics

# Job execution metrics
reconciliation_runs_total = Counter(
    "quay_reconciliation_runs_total",
    "total number of reconciliation runs completed",
    labelnames=["status"],  # success, failed
)
reconciliation_duration_seconds = Gauge(
    "quay_reconciliation_duration_seconds", "duration of last reconciliation run in seconds"
)
reconciliation_last_success_timestamp = Gauge(
    "quay_reconciliation_last_success_timestamp", "timestamp of last successful reconciliation"
)

# User state metrics
reconciliation_users_total = Gauge(
    "quay_reconciliation_users_total", "total number of active users in the database"
)
reconciliation_users_processed = Counter(
    "quay_reconciliation_users_processed_total",
    "total number of users successfully processed across all reconciliation runs",
)
reconciliation_users_not_processed = Counter(
    "quay_reconciliation_users_not_processed_total",
    "total number of users not processed across all reconciliation runs",
    labelnames=["reason"],
)

# API call metrics
reconciliation_api_calls = Counter(
    "quay_reconciliation_api_calls_total",
    "number of API calls made during reconciliation",
    labelnames=["api", "operation"],
)
reconciliation_api_call_duration = Histogram(
    "quay_reconciliation_api_call_duration_seconds",
    "time taken for API calls during reconciliation",
    labelnames=["api", "operation"],
    buckets=(1.0, 5.0, 20.0),  # Track fast (<1s), slow (1-5s), very slow/timeout (>5s)
)
reconciliation_api_call_errors = Counter(
    "quay_reconciliation_api_call_errors_total",
    "number of API call errors during reconciliation",
    labelnames=["api", "operation"],
)


@contextmanager
def track_api_call(api, operation):
    """
    Context manager to track API call count, duration, and errors.

    Usage:
        with track_api_call("marketplace_user", "lookup_customer_id"):
            result = user_api.lookup_customer_id(email)
    """
    reconciliation_api_calls.labels(api=api, operation=operation).inc()
    start_time = time.time()
    try:
        yield
    except Exception:
        reconciliation_api_call_errors.labels(api=api, operation=operation).inc()
        raise
    finally:
        duration = time.time() - start_time
        reconciliation_api_call_duration.labels(api=api, operation=operation).observe(duration)


def fetch_stripe_customer_plan(customer_id):
    """
    Fetch plan details for a Stripe customer.

    Args:
        customer_id: Stripe customer ID

    Returns:
        dict: Plan details (including 'rh_sku') or None if customer has no subscription

    Raises:
        stripe.error.APIConnectionError: Cannot connect to Stripe
        stripe.error.InvalidRequestError: Invalid customer ID
    """
    customer = stripe.Customer.retrieve(customer_id)

    # Check if customer has a subscription
    if not hasattr(customer, "subscription") or customer.subscription is None:
        return None

    # Check if subscription has a plan
    if not hasattr(customer.subscription, "plan") or customer.subscription.plan is None:
        return None

    return get_plan(customer.subscription.plan.id)


class ReconciliationWorker(Worker):
    def __init__(self):
        super(ReconciliationWorker, self).__init__()
        self.add_operation(
            self._reconcile_entitlements,
            app.config.get("RECONCILIATION_FREQUENCY", RECONCILIATION_FREQUENCY),
        )

    def _reconcile_entitlements(self, skip_lock_for_testing=False):
        """
        Performs reconciliation for user entitlements
        """
        # try to acquire lock
        if skip_lock_for_testing:
            self._perform_reconciliation(
                user_api=marketplace_users, marketplace_api=marketplace_subscriptions
            )
        else:
            try:
                with GlobalLock(
                    "RECONCILIATION_WORKER",
                    lock_ttl=app.config.get("RECONCILIATION_FREQUENCY", RECONCILIATION_FREQUENCY)
                    + LOCK_TIMEOUT_PADDING,
                ):
                    self._perform_reconciliation(
                        user_api=marketplace_users, marketplace_api=marketplace_subscriptions
                    )
            except LockNotAcquiredException:
                logger.debug("Could not acquire global lock for entitlement reconciliation")
                print(str(LockNotAcquiredException))

    def _perform_reconciliation(self, user_api, marketplace_api):
        """
        Core reconciliation logic.
        """
        start_time = time.time()

        try:
            logger.info("Reconciliation worker looking to create new subscriptions...")

            users = model.user.get_active_users(include_orgs=True)

            # Set gauge to current user count
            reconciliation_users_total.set(len(users))

            for user in users:
                if user.email is None or user.email == "":
                    reconciliation_users_not_processed.labels(reason="missing_email").inc()
                    logger.info("Email missing or empty for user %s", user.username)
                    continue

                customer_ids = []
                try:
                    with track_api_call("marketplace_user", "lookup_customer_id"):
                        customer_ids = user_api.lookup_customer_id(user.email, raise_exception=True)
                except MarketplaceApiException as e:
                    logger.error("Failed to lookup customer ID for %s: %s", user.email, str(e))
                if not customer_ids:
                    reconciliation_users_not_processed.labels(reason="no_customer_ids").inc()
                    logger.info("No web customer ids found for %s", user.email)
                    continue

                # Check if user has a Stripe subscription with a valid plan
                plan = None
                if user.stripe_id:
                    try:
                        plan = fetch_stripe_customer_plan(user.stripe_id)
                    except stripe.error.StripeError as e:
                        logger.error("Stripe error for user %s: %s", user.username, str(e))
                        reconciliation_users_not_processed.labels(reason="stripe_error").inc()
                        reconciliation_api_calls.labels(
                            api="stripe", operation="fetch_customer_plan"
                        ).inc()
                        continue
                if plan:
                    self._reconcile_paying_user(user, customer_ids, plan, marketplace_api)
                else:
                    self._reconcile_free_user(user, customer_ids, marketplace_api)

                reconciliation_users_processed.inc()
                logger.debug("Finished work for user %s", user.username)

            logger.info("Reconciliation worker is done")

            # Mark success
            reconciliation_runs_total.labels(status="success").inc()
            reconciliation_last_success_timestamp.set(time.time())

        except Exception:
            logger.exception("Reconciliation run failed")
            reconciliation_runs_total.labels(status="failed").inc()
            raise
        finally:
            duration = time.time() - start_time
            reconciliation_duration_seconds.set(duration)

    def _reconcile_paying_user(self, user, customer_ids, plan, marketplace_api):
        """
        Given a user with a paid Stripe plan, create any missing entitlements.

        Args:
            user: User object
            customer_ids: List of marketplace customer IDs
            plan: Plan dict containing 'rh_sku' key
            marketplace_api: Marketplace API client
        """
        for customer_id in customer_ids:
            rh_sku = plan.get("rh_sku")
            try:
                if not self._customer_id_has_sku(customer_id, rh_sku, marketplace_api):
                    self._create_entitlement(customer_id, rh_sku, marketplace_api)
            except MarketplaceApiException as e:
                logger.error(
                    "Failed to reconcile customer id (Free user). User:%s, customer_id: %s, error: %s",
                    user.username,
                    customer_id,
                    str(e),
                )
            # Not-implemented: Remove free tier sku entitlement for paying customers

    def _reconcile_free_user(self, user, customer_ids, marketplace_api):
        """
        Given a non-paying user, ensure they have the free-tier entitlement
        """
        for customer_id in customer_ids:
            try:
                if not self._customer_id_has_sku(customer_id, FREE_TIER_SKU, marketplace_api):
                    self._create_entitlement(customer_id, FREE_TIER_SKU, marketplace_api)
            except MarketplaceApiException as e:
                logger.error(
                    "Failed to reconcile customer id. User:%s, customer_id: %s, error: %s",
                    user.username,
                    customer_id,
                    str(e),
                )
            # Not-implemented: Remove duplicated free tier sku entitlements.

    def _create_entitlement(self, customer_id, sku, marketplace_api):
        with track_api_call("marketplace_subscription", "create_entitlement"):
            result = marketplace_api.create_entitlement(customer_id, sku, raise_exception=True)
            if result and result.ok:
                logger.info("Entitlement created. customer_id: %s, sku: %s", customer_id, sku)
            else:
                logger.error(
                    "Failed to create Entitlement. customer_id: %s, sku: %s", customer_id, sku
                )

    def _customer_id_has_sku(self, customer_id, sku, marketplace_api):
        with track_api_call("marketplace_subscription", "lookup_subscription"):
            subs = marketplace_api.lookup_subscription(customer_id, sku)
            return subs is not None and len(subs) > 0


def create_gunicorn_worker():
    """
    Follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread
    """
    worker = GunicornWorker(
        __name__, app, ReconciliationWorker(), features.ENTITLEMENT_RECONCILIATION
    )
    return worker


if __name__ == "__main__":
    if not features.ENTITLEMENT_RECONCILIATION:
        logger.debug("Reconciliation worker disabled; skipping")
        while True:
            time.sleep(1000)
    GlobalLock.configure(app.config)
    logger.debug("Starting reconciliation worker")
    worker = ReconciliationWorker()
    worker.start()
