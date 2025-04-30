import datetime
import logging
import time

import features
from app import app
from app import billing as stripe
from app import marketplace_subscriptions, marketplace_users
from data import model
from data.billing import RECONCILER_SKUS, RH_SKUS, get_plan
from util.locking import GlobalLock, LockNotAcquiredException
from workers.gunicorn_worker import GunicornWorker
from workers.namespacegcworker import LOCK_TIMEOUT_PADDING
from workers.worker import Worker

logger = logging.getLogger(__name__)

RECONCILIATION_TIMEOUT = 5 * 60  # 5min
LOCK_TIMEOUT_PADDING = 60  # 60
RECONCILIATION_FREQUENCY = 5 * 60  # run reconciliation every 5 min

MILLISECONDS_IN_SECONDS = 1000
SECONDS_IN_DAYS = 86400
ONE_MONTH = 30 * SECONDS_IN_DAYS * MILLISECONDS_IN_SECONDS

FREE_TIER_SKU = "MW04192"


class ReconciliationWorker(Worker):
    def __init__(self):
        super(ReconciliationWorker, self).__init__()
        self.add_operation(
            self._reconcile_entitlements,
            app.config.get("RECONCILIATION_FREQUENCY", RECONCILIATION_FREQUENCY),
        )

    def _perform_reconciliation(self, user_api, marketplace_api):
        """
        Gather all entitlements from internal marketplace api and store in quay db
        Create new entitlements for stripe customers if needed
        """
        logger.info("Reconciliation worker looking to create new subscriptions...")

        users = model.user.get_active_users(include_orgs=True)

        # stripe_users = [user for user in users if user.stripe_id is not None]

        for user in users:

            email = user.email

            # check against user api
            customer_ids = (
                user_api.lookup_customer_id(email) if email is not None and email != "" else None
            )
            if customer_ids is None:
                if email is None or email == "":
                    logger.info("Email missing or empty for user %s", user.username)
                logger.info("No web customer ids found for %s", email)
                continue

            logger.debug("Found %s number for %s", str(customer_ids), email)

            # check for any subscription reconciliations
            stripe_customer = None
            if user.stripe_id is not None:
                try:
                    stripe_customer = stripe.Customer.retrieve(user.stripe_id)
                except stripe.error.APIConnectionError:
                    logger.error("Cannot connect to Stripe")
                    continue
                except stripe.error.InvalidRequestError:
                    logger.warn("Invalid request for stripe_id %s", user.stripe_id)
                    continue

            self._iterate_over_ids(stripe_customer, customer_ids, marketplace_api, user.username)

            logger.debug("Finished work for user %s", user.username)

        logger.info("Reconciliation worker is done")

    def _iterate_over_ids(self, stripe_customer, customer_ids, marketplace_api, user=None):
        """
        Iterate over each customer's web id(s) and perform appropriate reconciliation actions
        """
        try:
            subscription = stripe_customer.subscription
        except AttributeError:
            subscription = None

        for customer_id in customer_ids:
            paying = False
            customer_skus = self._prefetch_user_entitlements(customer_id, marketplace_api)

            if stripe_customer is not None and subscription is not None:
                plan = get_plan(stripe_customer.subscription.plan.id)
                if plan is not None:
                    # check for missing sku
                    paying = True
                    plan_sku = plan.get("rh_sku")
                    if plan_sku not in customer_skus:
                        marketplace_api.create_entitlement(customer_id, plan_sku)
                        logger.info("Created SKU %s for %s", plan_sku, user)
                    # check for free tier sku
            else:
                # not a stripe customer but we want to check for paying subscriptions for the
                # next step
                if len(customer_skus) == 1 and customer_skus[0] == FREE_TIER_SKU:
                    # edge case where there is only one free sku present
                    paying = False
                else:
                    paying = len(customer_skus) > 0

            # check for free-tier reconciliations
            if not paying and FREE_TIER_SKU not in customer_skus:
                marketplace_api.create_entitlement(customer_id, FREE_TIER_SKU)
                logger.info("Created Free SKU %s for %s", FREE_TIER_SKU, user)
            elif paying and FREE_TIER_SKU in customer_skus:
                free_tier_subscriptions = marketplace_api.lookup_subscription(
                    customer_id, FREE_TIER_SKU
                )
                # api returns a list of subscriptions so we want to make sure we remove
                # all if there's more than one
                for sub in free_tier_subscriptions:
                    id = sub.get("id")
                    marketplace_api.remove_entitlement(id)
                    logger.info("Removed Free SKU id: %s from %s", id, user)

    def _prefetch_user_entitlements(self, customer_id, marketplace_api):
        found_skus = []
        for sku in RH_SKUS:
            subscription = marketplace_api.lookup_subscription(customer_id, sku)
            if subscription is not None and len(subscription) > 0:
                found_skus.append(sku)
        return found_skus

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
                    lock_ttl=RECONCILIATION_TIMEOUT + LOCK_TIMEOUT_PADDING,
                ):
                    self._perform_reconciliation(
                        user_api=marketplace_users, marketplace_api=marketplace_subscriptions
                    )
            except LockNotAcquiredException:
                logger.debug("Could not acquire global lock for entitlement reconciliation")
                print(str(LockNotAcquiredException))


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
