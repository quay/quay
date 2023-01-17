import logging

from data.database import (
    RedHatSubscriptions,
)

from data import model

logger = logging.getLogger(__name__)


def get_subscription_by_id(subscription_id):
    try:
        query = RedHatSubscriptions.get(RedHatSubscriptions.subscription_id == subscription_id)
        return query
    except RedHatSubscriptions.DoesNotExist:
        return None


def get_subscription_by_user(user_id):
    try:
        query = RedHatSubscriptions.get(RedHatSubscriptions.user_id == user_id)
        return query
    except RedHatSubscriptions.DoesNotExist:
        return None


def get_ebs_account_number(user_id):
    try:
        query = RedHatSubscriptions.get(RedHatSubscriptions.user_id == user_id).account_number
        return query
    except RedHatSubscriptions.DoesNotExist:
        return None


def save_ebs_account_number(user, ebsAccountNumber):
    try:
        query = RedHatSubscriptions.update(
            {RedHatSubscriptions.account_number: ebsAccountNumber}
        ).where(RedHatSubscriptions.user_id == user.id)
        query.execute()
    except model.DataModelException:
        logger.warning("Error saving account number for %s", user.username)


def update_subscription_end_date(sub_id, endDate):
    try:
        res = RedHatSubscriptions.update(
            {RedHatSubscriptions.subscription_end_date: endDate}
        ).where(RedHatSubscriptions.subscription_id == sub_id)
        res.execute()
    except RedHatSubscriptions.IntegrityError:
        logger.warning("problem updating end date of %s", sub_id)


def save_subscription(user_id, subscription_id, accountNumber, endDate, sku):
    try:
        return RedHatSubscriptions.create(
            user_id=user_id,
            subscription_id=subscription_id,
            account_number=accountNumber,
            subscription_end_date=endDate,
            sku_id=sku,
        )
    except model.DataModelException as ex:
        logger.debug(ex)
        return None
