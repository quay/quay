from bitbucket import BitBucket

from util.config.validators import BaseValidator, ConfigValidationException


class BitbucketTriggerValidator(BaseValidator):
    name = "bitbucket-trigger"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the config for BitBucket.
        """
        config = validator_context.config

        trigger_config = config.get("BITBUCKET_TRIGGER_CONFIG")
        if not trigger_config:
            raise ConfigValidationException("Missing client ID and client secret")

        if not trigger_config.get("CONSUMER_KEY"):
            raise ConfigValidationException("Missing Consumer Key")

        if not trigger_config.get("CONSUMER_SECRET"):
            raise ConfigValidationException("Missing Consumer Secret")

        key = trigger_config["CONSUMER_KEY"]
        secret = trigger_config["CONSUMER_SECRET"]
        callback_url = "%s/oauth1/bitbucket/callback/trigger/" % (
            validator_context.url_scheme_and_hostname.get_url()
        )

        bitbucket_client = BitBucket(key, secret, callback_url)
        (result, _, _) = bitbucket_client.get_authorization_url()
        if not result:
            raise ConfigValidationException("Invalid consumer key or secret")
