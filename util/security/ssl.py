from fnmatch import fnmatch

import OpenSSL


class CertInvalidException(Exception):
    """
    Exception raised when a certificate could not be parsed/loaded.
    """

    pass


class KeyInvalidException(Exception):
    """
    Exception raised when a key could not be parsed/loaded or successfully applied to a cert.
    """

    pass


def load_certificate(cert_contents):
    """
    Loads the certificate from the given contents and returns it or raises a CertInvalidException on
    failure.
    """
    try:
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_contents)
        return SSLCertificate(cert)
    except OpenSSL.crypto.Error as ex:
        raise CertInvalidException(ex.args[0][0][2])


_SUBJECT_ALT_NAME = b"subjectAltName"


class SSLCertificate(object):
    """
    Helper class for easier working with SSL certificates.
    """

    def __init__(self, openssl_cert):
        self.openssl_cert = openssl_cert

    def validate_private_key(self, private_key_path):
        """
        Validates that the private key found at the given file path applies to this certificate.

        Raises a KeyInvalidException on failure.
        """
        context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
        context.use_certificate(self.openssl_cert)

        try:
            context.use_privatekey_file(private_key_path)
            context.check_privatekey()
        except OpenSSL.SSL.Error as ex:
            raise KeyInvalidException(ex.args[0][0][2])

    def matches_name(self, check_name):
        """
        Returns true if this SSL certificate matches the given DNS hostname.
        """
        for dns_name in self.names:
            if fnmatch(check_name, dns_name):
                return True

        return False

    @property
    def expired(self):
        """
        Returns whether the SSL certificate has expired.
        """
        return self.openssl_cert.has_expired()

    @property
    def common_name(self):
        """
        Returns the defined common name for the certificate, if any.
        """
        return self.openssl_cert.get_subject().commonName

    @property
    def names(self):
        """
        Returns all the DNS named to which the certificate applies.

        May be empty.
        """
        dns_names = set()
        common_name = self.common_name
        if common_name is not None:
            dns_names.add(common_name)

        # Find the DNS extension, if any.
        for i in range(0, self.openssl_cert.get_extension_count()):
            ext = self.openssl_cert.get_extension(i)
            if ext.get_short_name() == _SUBJECT_ALT_NAME:
                value = str(ext)
                for san_name in value.split(","):
                    san_name_trimmed = san_name.strip()
                    if san_name_trimmed.startswith("DNS:"):
                        dns_names.add(san_name_trimmed[4:])

        return dns_names
