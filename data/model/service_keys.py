import re

from calendar import timegm
from datetime import datetime, timedelta
from peewee import JOIN

from authlib.jose import JsonWebKey

from data.database import db_for_update, User, ServiceKey, ServiceKeyApproval
from data.model import (
    ServiceKeyDoesNotExist,
    ServiceKeyAlreadyApproved,
    ServiceNameInvalid,
    db_transaction,
    config,
)
from data.model.notification import create_notification, delete_all_notifications_by_path_prefix


_SERVICE_NAME_REGEX = re.compile(r"^[a-z0-9_]+$")


def _expired_keys_clause(service):
    return (ServiceKey.service == service) & (ServiceKey.expiration_date <= datetime.utcnow())


def _stale_expired_keys_service_clause(service):
    return (ServiceKey.service == service) & _stale_expired_keys_clause()


def _stale_expired_keys_clause():
    expired_ttl = timedelta(seconds=config.app_config["EXPIRED_SERVICE_KEY_TTL_SEC"])
    return ServiceKey.expiration_date <= (datetime.utcnow() - expired_ttl)


def _stale_unapproved_keys_clause(service):
    unapproved_ttl = timedelta(seconds=config.app_config["UNAPPROVED_SERVICE_KEY_TTL_SEC"])
    return (
        (ServiceKey.service == service)
        & (ServiceKey.approval >> None)
        & (ServiceKey.created_date <= (datetime.utcnow() - unapproved_ttl))
    )


def _gc_expired(service):
    ServiceKey.delete().where(
        _stale_expired_keys_service_clause(service) | _stale_unapproved_keys_clause(service)
    ).execute()


def _verify_service_name(service_name):
    if not _SERVICE_NAME_REGEX.match(service_name):
        raise ServiceNameInvalid


def _notify_superusers(key):
    notification_metadata = {
        "name": key.name,
        "kid": key.kid,
        "service": key.service,
        "jwk": key.jwk,
        "metadata": key.metadata,
        "created_date": timegm(key.created_date.utctimetuple()),
    }

    if key.expiration_date is not None:
        notification_metadata["expiration_date"] = timegm(key.expiration_date.utctimetuple())

    if len(config.app_config["SUPER_USERS"]) > 0:
        superusers = User.select().where(User.username << config.app_config["SUPER_USERS"])
        for superuser in superusers:
            create_notification(
                "service_key_submitted",
                superuser,
                metadata=notification_metadata,
                lookup_path="/service_key_approval/{0}/{1}".format(key.kid, superuser.id),
            )


def create_service_key(name, kid, service, jwk, metadata, expiration_date, rotation_duration=None):
    _verify_service_name(service)
    _gc_expired(service)

    key = ServiceKey.create(
        name=name,
        kid=kid,
        service=service,
        jwk=jwk,
        metadata=metadata,
        expiration_date=expiration_date,
        rotation_duration=rotation_duration,
    )

    _notify_superusers(key)
    return key


def generate_service_key(
    service, expiration_date, kid=None, name="", metadata=None, rotation_duration=None
):
    """
    'kid' will default to the jwk thumbprint if not set explicitly.

    Reference: https://tools.ietf.org/html/rfc7638
    """
    options = {}
    if kid:
        options["kid"] = kid

    jwk = JsonWebKey.generate_key("RSA", 2048, is_private=True, options=options)
    kid = jwk.as_dict()["kid"]

    key = create_service_key(
        name,
        kid,
        service,
        jwk.as_dict(),
        metadata or {},
        expiration_date,
        rotation_duration=rotation_duration,
    )
    return (jwk.get_private_key(), key)


def replace_service_key(old_kid, kid, jwk, metadata, expiration_date):
    try:
        with db_transaction():
            key = db_for_update(ServiceKey.select().where(ServiceKey.kid == old_kid)).get()
            key.metadata.update(metadata)

            ServiceKey.create(
                name=key.name,
                kid=kid,
                service=key.service,
                jwk=jwk,
                metadata=key.metadata,
                expiration_date=expiration_date,
                rotation_duration=key.rotation_duration,
                approval=key.approval,
            )
            key.delete_instance()
    except ServiceKey.DoesNotExist:
        raise ServiceKeyDoesNotExist

    _notify_superusers(key)
    delete_all_notifications_by_path_prefix("/service_key_approval/{0}".format(old_kid))
    _gc_expired(key.service)


def update_service_key(kid, name=None, metadata=None):
    try:
        with db_transaction():
            key = db_for_update(ServiceKey.select().where(ServiceKey.kid == kid)).get()
            if name is not None:
                key.name = name

            if metadata is not None:
                key.metadata.update(metadata)

            key.save()
    except ServiceKey.DoesNotExist:
        raise ServiceKeyDoesNotExist


def delete_service_key(kid):
    try:
        key = ServiceKey.get(kid=kid)
        ServiceKey.delete().where(ServiceKey.kid == kid).execute()
    except ServiceKey.DoesNotExist:
        raise ServiceKeyDoesNotExist

    delete_all_notifications_by_path_prefix("/service_key_approval/{0}".format(kid))
    _gc_expired(key.service)
    return key


def set_key_expiration(kid, expiration_date):
    try:
        service_key = get_service_key(kid, alive_only=False, approved_only=False)
    except ServiceKey.DoesNotExist:
        raise ServiceKeyDoesNotExist

    service_key.expiration_date = expiration_date
    service_key.save()


def approve_service_key(kid, approval_type, approver=None, notes=""):
    try:
        with db_transaction():
            key = db_for_update(ServiceKey.select().where(ServiceKey.kid == kid)).get()
            if key.approval is not None:
                raise ServiceKeyAlreadyApproved

            approval = ServiceKeyApproval.create(
                approver=approver, approval_type=approval_type, notes=notes
            )
            key.approval = approval
            key.save()
    except ServiceKey.DoesNotExist:
        raise ServiceKeyDoesNotExist

    delete_all_notifications_by_path_prefix("/service_key_approval/{0}".format(kid))
    return key


def _list_service_keys_query(
    kid=None, service=None, approved_only=True, alive_only=True, approval_type=None
):
    query = ServiceKey.select().join(ServiceKeyApproval, JOIN.LEFT_OUTER)

    if approved_only:
        query = query.where(~(ServiceKey.approval >> None))

    if alive_only:
        query = query.where(
            (ServiceKey.expiration_date > datetime.utcnow()) | (ServiceKey.expiration_date >> None)
        )

    if approval_type is not None:
        query = query.where(ServiceKeyApproval.approval_type == approval_type)

    if service is not None:
        query = query.where(ServiceKey.service == service)
        query = query.where(
            ~(_expired_keys_clause(service)) | ~(_stale_unapproved_keys_clause(service))
        )

    if kid is not None:
        query = query.where(ServiceKey.kid == kid)

    query = query.where(~(_stale_expired_keys_clause()) | (ServiceKey.expiration_date >> None))
    return query


def list_all_keys():
    return list(_list_service_keys_query(approved_only=False, alive_only=False))


def list_service_keys(service):
    return list(_list_service_keys_query(service=service))


def get_service_key(kid, service=None, alive_only=True, approved_only=True):
    try:
        return _list_service_keys_query(
            kid=kid, service=service, approved_only=approved_only, alive_only=alive_only
        ).get()
    except ServiceKey.DoesNotExist:
        raise ServiceKeyDoesNotExist
