from util.config.validators import BaseValidator, ConfigValidationException
from util.security.ssl import load_certificate, CertInvalidException, KeyInvalidException

SSL_FILENAMES = ["ssl.cert", "ssl.key"]


class SSLValidator(BaseValidator):
    name = "ssl"

    @classmethod
    def validate(cls, validator_context):
        """
        Validates the SSL configuration (if enabled).
        """
        config = validator_context.config
        config_provider = validator_context.config_provider

        # Skip if non-SSL.
        if config.get("PREFERRED_URL_SCHEME", "http") != "https":
            return

        # Skip if externally terminated.
        if config.get("EXTERNAL_TLS_TERMINATION", False) is True:
            return

        # Verify that we have all the required SSL files.
        for filename in SSL_FILENAMES:
            if not config_provider.volume_file_exists(filename):
                raise ConfigValidationException("Missing required SSL file: %s" % filename)

        # Read the contents of the SSL certificate.
        with config_provider.get_volume_file(SSL_FILENAMES[0], mode="rb") as f:
            cert_contents = f.read()

        # Validate the certificate.
        try:
            certificate = load_certificate(cert_contents)
        except CertInvalidException as cie:
            raise ConfigValidationException("Could not load SSL certificate: %s" % cie)

        # Verify the certificate has not expired.
        if certificate.expired:
            raise ConfigValidationException("The specified SSL certificate has expired.")

        # Verify the hostname matches the name in the certificate.
        if not certificate.matches_name(_ssl_cn(config["SERVER_HOSTNAME"])):
            msg = 'Supported names "%s" in SSL cert do not match server hostname "%s"' % (
                ", ".join(list(certificate.names)),
                _ssl_cn(config["SERVER_HOSTNAME"]),
            )
            raise ConfigValidationException(msg)

        # Verify the private key against the certificate.
        private_key_path = None
        with config_provider.get_volume_file(SSL_FILENAMES[1]) as f:
            private_key_path = f.name

        if not private_key_path:
            # Only in testing.
            return

        try:
            certificate.validate_private_key(private_key_path)
        except KeyInvalidException as kie:
            raise ConfigValidationException("SSL private key failed to validate: %s" % kie)


def _ssl_cn(server_hostname):
    """
    Return the common name (fully qualified host name) from the SERVER_HOSTNAME.
    """
    host_port = server_hostname.rsplit(":", 1)

    # SERVER_HOSTNAME includes the port
    if len(host_port) == 2:
        if host_port[-1].isdigit():
            return host_port[-2]

    return server_hostname
