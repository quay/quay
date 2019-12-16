from storage import get_storage_driver, TYPE_LOCAL_STORAGE
from util.config.validators import BaseValidator, ConfigValidationException


class StorageValidator(BaseValidator):
    name = "registry-storage"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates registry storage.
        """
        config = validator_context.config
        client = validator_context.http_client
        ip_resolver = validator_context.ip_resolver
        config_provider = validator_context.config_provider

        replication_enabled = config.get("FEATURE_STORAGE_REPLICATION", False)

        providers = list(_get_storage_providers(config, ip_resolver, config_provider).items())
        if not providers:
            raise ConfigValidationException("Storage configuration required")

        for name, (storage_type, driver) in providers:
            # We can skip localstorage validation, since we can't guarantee that
            # this will be the same machine Q.E. will run under
            if storage_type == TYPE_LOCAL_STORAGE:
                continue

            try:
                if replication_enabled and storage_type == "LocalStorage":
                    raise ConfigValidationException(
                        "Locally mounted directory not supported " + "with storage replication"
                    )

                # Run validation on the driver.
                driver.validate(client)

                # Run setup on the driver if the read/write succeeded.
                driver.setup()
            except Exception as ex:
                msg = str(ex).strip().split("\n")[0]
                raise ConfigValidationException(
                    "Invalid storage configuration: %s: %s" % (name, msg)
                )


def _get_storage_providers(config, ip_resolver, config_provider):
    storage_config = config.get("DISTRIBUTED_STORAGE_CONFIG", {})
    drivers = {}

    try:
        for name, parameters in list(storage_config.items()):
            driver = get_storage_driver(None, None, config_provider, ip_resolver, parameters)
            drivers[name] = (parameters[0], driver)
    except TypeError:
        raise ConfigValidationException("Missing required parameter(s) for storage %s" % name)

    return drivers
