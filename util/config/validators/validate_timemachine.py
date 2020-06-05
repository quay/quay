import logging

from util.config.validators import BaseValidator, ConfigValidationException
from util.timedeltastring import convert_to_timedelta

logger = logging.getLogger(__name__)


class TimeMachineValidator(BaseValidator):
    name = "time-machine"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config

        if not "DEFAULT_TAG_EXPIRATION" in config:
            # Old style config
            return

        try:
            convert_to_timedelta(config["DEFAULT_TAG_EXPIRATION"]).total_seconds()
        except ValueError as ve:
            raise ConfigValidationException("Invalid default expiration: %s" % str(ve))

        if not config["DEFAULT_TAG_EXPIRATION"] in config.get("TAG_EXPIRATION_OPTIONS", []):
            raise ConfigValidationException("Default expiration must be in expiration options set")

        for ts in config.get("TAG_EXPIRATION_OPTIONS", []):
            try:
                convert_to_timedelta(ts)
            except ValueError as ve:
                raise ConfigValidationException("Invalid tag expiration option: %s" % ts)
