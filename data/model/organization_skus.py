import logging

import peewee

from data import model
from data.database import OrganizationRhSkus, db_transaction

logger = logging.getLogger(__name__)


def get_org_subscriptions(org_id):
    try:
        query = OrganizationRhSkus.select().where(OrganizationRhSkus.org_id == org_id)
        return query
    except OrganizationRhSkus.DoesNotExist:
        return None


def bind_subscription_to_org(subscription_id, org_id, user_id, quantity=1):
    try:
        return OrganizationRhSkus.create(
            subscription_id=subscription_id, org_id=org_id, user_id=user_id, quantity=quantity
        )
    except model.DataModelException as ex:
        logger.error("Problem binding subscription to org %s: %s", org_id, ex)
    except peewee.IntegrityError:
        raise model.OrgSubscriptionBindingAlreadyExists()


def subscription_bound_to_org(subscription_id):
    # lookup row in table matching subscription_id, if there is no row return false, otherwise return true
    # this function is used to check if a subscription is bound to an org or
    try:
        query = (
            OrganizationRhSkus.select()
            .where(OrganizationRhSkus.subscription_id == subscription_id)
            .dicts()
        )
        if query.__len__() > 0:
            return True, query
        return False, None
    except OrganizationRhSkus.DoesNotExist:
        return False, None


def remove_subscription_from_org(org_id, subscription_id):
    query = OrganizationRhSkus.delete().where(
        OrganizationRhSkus.org_id == org_id,
        OrganizationRhSkus.subscription_id == subscription_id,
    )
    query.execute()


def remove_all_owner_subscriptions_from_org(user_id, org_id):
    try:
        query = OrganizationRhSkus.delete().where(
            OrganizationRhSkus.user_id == user_id,
            OrganizationRhSkus.org_id == org_id,
        )
        query.execute()
    except model.DataModelException as ex:
        raise model.DataModelException(ex)


def get_bound_subscriptions(subscription_id):
    try:
        query = OrganizationRhSkus.select().where(
            OrganizationRhSkus.subscription_id == subscription_id
        )
        return query
    except OrganizationRhSkus.DoesNotExist:
        return None
