import datetime
import logging
import time

import features
from app import app
from app import billing as stripe
from app import marketplace_subscriptions, marketplace_users
from data import model
from data.billing import RH_SKUS, get_plan
from data.model import entitlements
from util import marketplace
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


class ReconciliationWorker(Worker):
    def __init__(self):
        super(ReconciliationWorker, self).__init__()
        self.add_operation(
            self._reconcile_entitlements,
            app.config.get("RECONCILIATION_FREQUENCY", RECONCILIATION_FREQUENCY),
        )

    def _check_stripe_matches_sku(self, user, sku):
        """
        Check if user's stripe plan matches with RH sku
        """
        stripe_id = user.stripe_id

        if stripe_id is None:
            return False

        stripe_customer = stripe.Customer.retrieve(stripe_id)
        if stripe_customer is None:
            logger.debug("user %s has no valid subscription on stripe", user.username)
            return False

        if stripe_customer.subscription:
            plan = get_plan(stripe_customer.subscription.plan.id)
            if plan is None:
                return False

            if plan.get("rh_sku") == sku:
                return True

        return False

    def _perform_reconciliation(self, user_api, marketplace_api):
        """
        Gather all entitlements from internal marketplace api and store in quay db
        Create new entitlements for stripe customers if needed
        """
        logger.info("Reconciliation worker looking to create new subscriptions...")

        users = model.user.get_active_users()

        stripe_users = [user for user in users if user.stripe_id is not None]

        for user in stripe_users:

            email = user.email
            ebsAccountNumber = entitlements.get_ebs_account_number(user.id)
            logger.debug(
                "Database returned %s account number for %s", str(ebsAccountNumber), user.username
            )

            # go to user api if no ebsAccountNumber is found
            if ebsAccountNumber is None:
                logger.debug("Looking up ebsAccountNumber for email %s", email)
                ebsAccountNumber = user_api.lookup_customer_id(email)
                logger.debug("Found %s number for %s", str(ebsAccountNumber), user.username)
                if ebsAccountNumber:
                    entitlements.save_ebs_account_number(user, ebsAccountNumber)
                else:
                    logger.debug("User %s does not have an account number", user.username)
                    continue

            # check if we need to create a subscription for customer in RH marketplace
            for sku_id in RH_SKUS:
                if self._check_stripe_matches_sku(user, sku_id):
                    subscription = marketplace_api.lookup_subscription(ebsAccountNumber, sku_id)
                    if subscription is None:
                        marketplace_api.create_entitlement(ebsAccountNumber, sku_id)
                    break

            logger.debug("Finished work for user %s", user.username)

        logger.info("Reconciliation worker is done")

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
