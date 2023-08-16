import logging

from data import model
from data.database import RedHatSubscriptions

logger = logging.getLogger(__name__)


def get_ebs_account_number(user_id):
    try:
        query = RedHatSubscriptions.get(RedHatSubscriptions.user_id == user_id).account_number
        return query
    except RedHatSubscriptions.DoesNotExist:
        return None


def save_ebs_account_number(user, ebsAccountNumber):
    try:
        return RedHatSubscriptions.create(user_id=user.id, account_number=ebsAccountNumber)
    except model.DataModelException as ex:
        logger.error("Problem saving account number for %s: %s", user.username, ex)
