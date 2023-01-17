import datetime
import logging
import random
import time


import features
from app import app
from app import billing as stripe
from data import marketplace, model
from data.billing import get_plan
from data.database import QuaySkuProperties
from data.model import entitlements
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
        stripe_customer = stripe.Customer.retrieve(user.stripe_id)
        logger.debug("stripe customer = %s", stripe_customer)
        if stripe_customer is None:
            logger.debug("user %s has no valid subscription on stripe", user.username)
            return False

        plan = get_plan(stripe_customer.subscription.plan.id)
        if plan["privateRepos"] == sku.value:
            return True

        logger.debug("stripe plan and sku %s do not match for %s", sku.name, user.username)
        return False

    def _perform_reconciliation(self, user_api, marketplace_api):
        """
        Gather all entitlements from internal marketplace api and store in quay db
        Create new entitlements for stripe customers if needed
        """
        logger.info("Reconciliation worker is gathering entitlements...")

        users = model.user.get_active_users()

        for user in users:

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

            for sku in QuaySkuProperties:
                # Check each sku since user can have multiple subscriptions
                rh_sku = sku.name

                if ebsAccountNumber is None:
                    logger.debug("No account found for %s", user.username)
                    break

                subscription = marketplace_api.lookup_subscription(ebsAccountNumber, rh_sku)

                # If there is no subscription, we need to create one for them
                if subscription is None and user.stripe_id:
                    logger.debug("Checking if we need to create subscription for %s", user.username)
                    if self._check_stripe_matches_sku(user, sku):
                        logger.debug("Will create %s for %s", rh_sku, user.username)
                        marketplace_api.create_entitlement(ebsAccountNumber, rh_sku)
                    continue
                elif subscription is None and not user.stripe_id:
                    logger.debug(
                        "User %s is not on stripe, will not create entitlement for them",
                        user.username,
                    )
                    continue

                subscription_id = subscription["id"]
                endDate = subscription["effectiveEndDate"]
                # convert endDate from big int to datetime for adding to RedHatSubscriptions table
                endDateDatetime = datetime.datetime.fromtimestamp(endDate / MILLISECONDS_IN_SECONDS)

                # store subscription in the database if it is not already in there
                local_subscription = entitlements.get_subscription_by_id(subscription_id)
                if local_subscription is None:
                    logger.debug(
                        "Adding new subscription %s to database for user %s",
                        rh_sku,
                        user.username,
                    )
                    entitlements.save_subscription(
                        user.id, subscription_id, ebsAccountNumber, endDateDatetime, rh_sku
                    )
                elif local_subscription.subscription_end_date < endDateDatetime:
                    entitlements.update_subscription_end_date(subscription_id, endDateDatetime)

                # Checking if subscription needs to be extended
                if endDate is not None and user.stripe_id:
                    # validate user's stripe end date are the same in marketplace
                    stripe_customer = stripe.Customer.retrieve(user.stripe_id)
                    stripe_endDate = stripe_customer.subscription.current_period_end

                    if endDate < stripe_endDate and self._check_stripe_matches_sku(user, sku):
                        logger.debug("Found subscription to extend")
                        endDate = stripe_endDate  # change to stripe end date
                        marketplace_api.extend_subscription(subscription_id, endDate)

            logger.debug("Finished work for user %s", user.username)

        logger.info("Reconciliation worker is done")

    def _reconcile_entitlements(self, skip_lock_for_testing=True):
        """
        Performs reconciliation for user entitlements
        """
        internal_user_api = marketplace.UserAPI(app.config)
        internal_marketplace_api = marketplace.MarketplaceAPI(app.config)
        # generate random wait
        random_wait = random.randint(1, 100)
        time.sleep(random_wait)
        # try to acquire lock
        if skip_lock_for_testing:
            self._perform_reconciliation(
                user_api=internal_user_api, marketplace_api=internal_marketplace_api
            )
        else:
            try:
                with GlobalLock(
                    "RECONCILIATION_WORKER",
                    lock_ttl=RECONCILIATION_TIMEOUT + LOCK_TIMEOUT_PADDING,
                ):
                    self._perform_reconciliation(
                        user_api=internal_user_api, marketplace_api=internal_marketplace_api
                    )
            except LockNotAcquiredException:
                logger.debug("Could not acquire global lock for entitlement reconciliation")
                print(str(LockNotAcquiredException))


def create_gunicorn_worker():
    """
    Follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread
    """
    if not features.ENTITLEMENT_RECONCILIATION:
        logger.debug("Reconciler disabled, skipping")
        return None
    g_worker = GunicornWorker(__name__, app, ReconciliationWorker(), True)
    return g_worker


if __name__ == "__main__":
    if not features.ENTITLEMENT_RECONCILIATION:
        logger.debug("Reconciliation worker disabled; skipping")
        while True:
            time.sleep(1000)
    GlobalLock.configure(app.config)
    logger.debug("Starting reconciliation worker")
    worker = ReconciliationWorker()
    worker.start()
