import data.model

from endpoints.keyserver.models_interface import (
    KeyServerDataInterface,
    ServiceKey,
    ServiceKeyDoesNotExist,
)


class PreOCIModel(KeyServerDataInterface):
    """
    PreOCIModel implements the data model for JWT key service using a database schema before it was
    changed to support the OCI specification.
    """

    def list_service_keys(self, service):
        return data.model.service_keys.list_service_keys(service)

    def get_service_key(self, signer_kid, service=None, alive_only=True, approved_only=True):
        try:
            key = data.model.service_keys.get_service_key(
                signer_kid, service, alive_only, approved_only
            )
            return _db_key_to_servicekey(key)
        except data.model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist()

    def create_service_key(
        self, name, kid, service, jwk, metadata, expiration_date, rotation_duration=None
    ):
        key = data.model.service_keys.create_service_key(
            name, kid, service, jwk, metadata, expiration_date, rotation_duration
        )
        return _db_key_to_servicekey(key)

    def replace_service_key(self, old_kid, kid, jwk, metadata, expiration_date):
        try:
            data.model.service_keys.replace_service_key(
                old_kid, kid, jwk, metadata, expiration_date
            )
        except data.model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist()

    def delete_service_key(self, kid):
        try:
            key = data.model.service_keys.delete_service_key(kid)
            return _db_key_to_servicekey(key)
        except data.model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist()


pre_oci_model = PreOCIModel()


def _db_key_to_servicekey(key):
    """
    Converts the Pre-OCI database model of a service key into a ServiceKey.
    """
    return ServiceKey(
        name=key.name,
        kid=key.kid,
        service=key.service,
        jwk=key.jwk,
        metadata=key.metadata,
        created_date=key.created_date,
        expiration_date=key.expiration_date,
        rotation_duration=key.rotation_duration,
        approval=key.approval,
    )
