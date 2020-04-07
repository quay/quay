import os
import ldap
import subprocess

from data.users import LDAP_CERT_FILENAME
from data.users.externalldap import LDAPConnection, LDAPUsers
from util.config.validators import BaseValidator, ConfigValidationException


class LDAPValidator(BaseValidator):
    name = "ldap"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the LDAP connection.
        """
        config = validator_context.config
        config_provider = validator_context.config_provider
        init_scripts_location = validator_context.init_scripts_location

        if config.get("AUTHENTICATION_TYPE", "Database") != "LDAP":
            return

        # If there is a custom LDAP certificate, then reinstall the certificates for the container.
        if config_provider.volume_file_exists(LDAP_CERT_FILENAME):
            subprocess.check_call(
                [os.path.join(init_scripts_location, "certs_install.sh")],
                env={"QUAYCONFIG": config_provider.get_config_dir_path()},
            )

        # Note: raises ldap.INVALID_CREDENTIALS on failure
        admin_dn = config.get("LDAP_ADMIN_DN")
        admin_passwd = config.get("LDAP_ADMIN_PASSWD")

        if not admin_dn:
            raise ConfigValidationException("Missing Admin DN for LDAP configuration")

        if not admin_passwd:
            raise ConfigValidationException("Missing Admin Password for LDAP configuration")

        ldap_uri = config.get("LDAP_URI", "ldap://localhost")
        if not ldap_uri.startswith("ldap://") and not ldap_uri.startswith("ldaps://"):
            raise ConfigValidationException("LDAP URI must start with ldap:// or ldaps://")

        allow_tls_fallback = config.get("LDAP_ALLOW_INSECURE_FALLBACK", False)

        try:
            with LDAPConnection(ldap_uri, admin_dn, admin_passwd, allow_tls_fallback):
                pass
        except ldap.LDAPError as ex:
            values = ex.args[0] if ex.args else {}
            if not isinstance(values, dict):
                raise ConfigValidationException(str(ex.args))

            raise ConfigValidationException(values.get("desc", "Unknown error"))

        base_dn = config.get("LDAP_BASE_DN")
        user_rdn = config.get("LDAP_USER_RDN", [])
        uid_attr = config.get("LDAP_UID_ATTR", "uid")
        email_attr = config.get("LDAP_EMAIL_ATTR", "mail")
        email_attr = config.get("LDAP_EMAIL_ATTR", "mail")
        ldap_user_filter = config.get("LDAP_USER_FILTER", None)

        if ldap_user_filter:
            if not ldap_user_filter.startswith("(") or not ldap_user_filter.endswith(")"):
                raise ConfigValidationException("LDAP user filter must be wrapped in parentheses")

        users = LDAPUsers(
            ldap_uri,
            base_dn,
            admin_dn,
            admin_passwd,
            user_rdn,
            uid_attr,
            email_attr,
            allow_tls_fallback,
            ldap_user_filter=ldap_user_filter,
        )

        # Ensure at least one user exists to verify the connection is setup properly.
        (result, err_msg) = users.at_least_one_user_exists()
        if not result:
            msg = (
                "Verification that users exist failed: %s. \n\nNo users exist "
                + "in the remote authentication system "
                + "OR LDAP auth is misconfigured."
            ) % err_msg
            raise ConfigValidationException(msg)
