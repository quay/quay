from tempfile import NamedTemporaryFile

import pytest

from OpenSSL import crypto

from util.security.ssl import load_certificate, CertInvalidException, KeyInvalidException


def generate_test_cert(hostname="somehostname", san_list=None, expires=1000000):
    """
    Generates a test SSL certificate and returns the certificate data and private key data.
    """

    # Based on: http://blog.richardknop.com/2012/08/create-a-self-signed-x509-certificate-in-python/
    # Create a key pair.
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)

    # Create a self-signed cert.
    cert = crypto.X509()
    cert.get_subject().CN = hostname

    # Add the subjectAltNames (if necessary).
    if san_list is not None:
        cert.add_extensions([crypto.X509Extension(b"subjectAltName", False, b", ".join(san_list))])

    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(expires)
    cert.set_issuer(cert.get_subject())

    cert.set_pubkey(k)
    cert.sign(k, "sha1")

    # Dump the certificate and private key in PEM format.
    cert_data = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    key_data = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)

    return (cert_data, key_data)


def test_load_certificate():
    # Try loading an invalid certificate.
    with pytest.raises(CertInvalidException):
        load_certificate("someinvalidcontents")

    # Load a valid certificate.
    (public_key_data, _) = generate_test_cert()

    cert = load_certificate(public_key_data)
    assert not cert.expired
    assert cert.names == set(["somehostname"])
    assert cert.matches_name("somehostname")


def test_expired_certificate():
    (public_key_data, _) = generate_test_cert(expires=-100)

    cert = load_certificate(public_key_data)
    assert cert.expired


def test_hostnames():
    (public_key_data, _) = generate_test_cert(hostname="foo", san_list=[b"DNS:bar", b"DNS:baz"])
    cert = load_certificate(public_key_data)
    assert cert.names == set(["foo", "bar", "baz"])

    for name in cert.names:
        assert cert.matches_name(name)


def test_wildcard_hostnames():
    (public_key_data, _) = generate_test_cert(hostname="foo", san_list=[b"DNS:*.bar"])
    cert = load_certificate(public_key_data)
    assert cert.names == set(["foo", "*.bar"])

    for name in cert.names:
        assert cert.matches_name(name)

    assert cert.matches_name("something.bar")
    assert cert.matches_name("somethingelse.bar")
    assert cert.matches_name("cool.bar")
    assert not cert.matches_name("*")


def test_nondns_hostnames():
    (public_key_data, _) = generate_test_cert(hostname="foo", san_list=[b"URI:yarg"])
    cert = load_certificate(public_key_data)
    assert cert.names == set(["foo"])


def test_validate_private_key():
    (public_key_data, private_key_data) = generate_test_cert()

    private_key = NamedTemporaryFile(delete=True)
    private_key.write(private_key_data)
    private_key.seek(0)

    cert = load_certificate(public_key_data)
    cert.validate_private_key(private_key.name)


def test_invalid_private_key():
    (public_key_data, _) = generate_test_cert()

    private_key = NamedTemporaryFile(delete=True)
    private_key.write(b"somerandomdata")
    private_key.seek(0)

    cert = load_certificate(public_key_data)
    with pytest.raises(KeyInvalidException):
        cert.validate_private_key(private_key.name)


def test_mismatch_private_key():
    (public_key_data, _) = generate_test_cert()
    (_, private_key_data) = generate_test_cert()

    private_key = NamedTemporaryFile(delete=True)
    private_key.write(private_key_data)
    private_key.seek(0)

    cert = load_certificate(public_key_data)
    with pytest.raises(KeyInvalidException):
        cert.validate_private_key(private_key.name)
