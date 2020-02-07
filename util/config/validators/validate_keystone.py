from util.config.validators import BaseValidator, ConfigValidationException
from data.users.keystone import get_keystone_users


class KeystoneValidator(BaseValidator):
    name = "keystone"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the Keystone authentication system.
        """
        config = validator_context.config

        if config.get("AUTHENTICATION_TYPE", "Database") != "Keystone":
            return

        auth_url = config.get("KEYSTONE_AUTH_URL")
        auth_version = int(config.get("KEYSTONE_AUTH_VERSION", 2))
        admin_username = config.get("KEYSTONE_ADMIN_USERNAME")
        admin_password = config.get("KEYSTONE_ADMIN_PASSWORD")
        admin_tenant = config.get("KEYSTONE_ADMIN_TENANT")

        if not auth_url:
            raise ConfigValidationException("Missing authentication URL")

        if not admin_username:
            raise ConfigValidationException("Missing admin username")

        if not admin_password:
            raise ConfigValidationException("Missing admin password")

        if not admin_tenant:
            raise ConfigValidationException("Missing admin tenant")

        requires_email = config.get("FEATURE_MAILING", True)
        users = get_keystone_users(
            auth_version, auth_url, admin_username, admin_password, admin_tenant, requires_email
        )

        # Verify that the superuser exists. If not, raise an exception.
        (result, err_msg) = users.at_least_one_user_exists()
        if not result:
            msg = (
                "Verification that users exist failed: %s. \n\nNo users exist "
                + "in the admin tenant/project "
                + "in the remote authentication system "
                + "OR Keystone auth is misconfigured."
            ) % err_msg
            raise ConfigValidationException(msg)
