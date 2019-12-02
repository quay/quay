from data import model

from config_app.config_endpoints.api.superuser_models_interface import (
    SuperuserDataInterface,
    User,
    ServiceKey,
    Approval,
)


def _create_user(user):
    if user is None:
        return None
    return User(user.username, user.email, user.verified, user.enabled, user.robot)


def _create_key(key):
    approval = None
    if key.approval is not None:
        approval = Approval(
            _create_user(key.approval.approver),
            key.approval.approval_type,
            key.approval.approved_date,
            key.approval.notes,
        )

    return ServiceKey(
        key.name,
        key.kid,
        key.service,
        key.jwk,
        key.metadata,
        key.created_date,
        key.expiration_date,
        key.rotation_duration,
        approval,
    )


class ServiceKeyDoesNotExist(Exception):
    pass


class ServiceKeyAlreadyApproved(Exception):
    pass


class PreOCIModel(SuperuserDataInterface):
    """
  PreOCIModel implements the data model for the SuperUser using a database schema
  before it was changed to support the OCI specification.
  """

    def list_all_service_keys(self):
        keys = model.service_keys.list_all_keys()
        return [_create_key(key) for key in keys]

    def approve_service_key(self, kid, approval_type, notes=""):
        try:
            key = model.service_keys.approve_service_key(kid, approval_type, notes=notes)
            return _create_key(key)
        except model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist
        except model.ServiceKeyAlreadyApproved:
            raise ServiceKeyAlreadyApproved

    def generate_service_key(
        self, service, expiration_date, kid=None, name="", metadata=None, rotation_duration=None
    ):
        (private_key, key) = model.service_keys.generate_service_key(
            service, expiration_date, metadata=metadata, name=name
        )

        return private_key, key.kid


pre_oci_model = PreOCIModel()
