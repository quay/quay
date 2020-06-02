from io import StringIO

from util.config.validators import BaseValidator, ConfigValidationException
from util.security.signing import SIGNING_ENGINES


class SignerValidator(BaseValidator):
    name = "signer"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the GPG public+private key pair used for signing converted ACIs.
        """
        config = validator_context.config
        config_provider = validator_context.config_provider

        if config.get("SIGNING_ENGINE") is None:
            return

        if config["SIGNING_ENGINE"] not in SIGNING_ENGINES:
            raise ConfigValidationException("Unknown signing engine: %s" % config["SIGNING_ENGINE"])

        engine = SIGNING_ENGINES[config["SIGNING_ENGINE"]](config, config_provider)
        engine.detached_sign(BytesIO(b"test string"))
