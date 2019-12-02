from util.config.validators import BaseValidator, ConfigValidationException


class ActionLogArchivingValidator(BaseValidator):
    name = "actionlogarchiving"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config

        """ Validates the action log archiving configuration. """
        if not config.get("FEATURE_ACTION_LOG_ROTATION", False):
            return

        if not config.get("ACTION_LOG_ARCHIVE_PATH"):
            raise ConfigValidationException("Missing action log archive path")

        if not config.get("ACTION_LOG_ARCHIVE_LOCATION"):
            raise ConfigValidationException("Missing action log archive storage location")

        location = config["ACTION_LOG_ARCHIVE_LOCATION"]
        storage_config = config.get("DISTRIBUTED_STORAGE_CONFIG") or {}
        if location not in storage_config:
            msg = "Action log archive storage location `%s` not found in storage config" % location
            raise ConfigValidationException(msg)
