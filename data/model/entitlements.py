import logging

from data import model
from data.database import RedHatSubscriptions

logger = logging.getLogger(__name__)


def get_web_customer_ids(user_id):
    try:
        customer_ids = [
            customer.account_number
            for customer in RedHatSubscriptions.select().where(
                RedHatSubscriptions.user_id == user_id
            )
        ]
        if len(customer_ids) == 0:
            return None
        return customer_ids
    except RedHatSubscriptions.DoesNotExist:
        return None


def save_web_customer_id(user, web_customer_id):
    try:
        return RedHatSubscriptions.create(user_id=user.id, account_number=web_customer_id)
    except model.DataModelException as ex:
        logger.error("Problem saving account number for %s: %s", user.username, ex)


def update_web_customer_id(user, web_customer_id):
    try:
        query = RedHatSubscriptions.update(
            {RedHatSubscriptions.account_number: web_customer_id}
        ).where(RedHatSubscriptions.user_id == user.id)
        query.execute()
    except model.DataModelException as ex:
        logger.error("Problem updating customer id for %s: %s", user.username, ex)


def remove_web_customer_id(user, web_customer_id):
    try:
        customer_id = RedHatSubscriptions.get(
            RedHatSubscriptions.user_id == user.id,
            RedHatSubscriptions.account_number == web_customer_id,
        )
        return customer_id.delete_instance()
    except model.DataModelException as ex:
        logger.error("Problem removing customer id for %s: %s", user.username, ex)
