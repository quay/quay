from datetime import datetime, timedelta, timezone
from tempfile import NamedTemporaryFile

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from util.security.ssl import (
    CertInvalidException,
    KeyInvalidException,
    load_certificate,
)


def generate_test_cert(hostname="somehostname", san_list=None, expires=1000000):
    """
    Generates a test SSL certificate and returns the certificate data and private key data.
    """

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1000)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(seconds=expires))
    )

    if san_list is not None:
        builder = builder.add_extension(x509.SubjectAlternativeName(san_list), critical=False)

    cert = builder.sign(key, hashes.SHA256())
    cert_data = cert.public_bytes(serialization.Encoding.PEM)
    key_data = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )

    return (cert_data, key_data)


def test_load_certificate():
    # Try loading an invalid certificate.
    with pytest.raises(CertInvalidException):
        load_certificate("someinvalidcontents")

    # Load a valid certificate.
    public_key_data, _ = generate_test_cert()

    cert = load_certificate(public_key_data)
    assert not cert.expired
    assert cert.names == set(["somehostname"])
    assert cert.matches_name("somehostname")


def test_expired_certificate():
    public_key_data, _ = generate_test_cert(expires=-100)

    cert = load_certificate(public_key_data)
    assert cert.expired


def test_hostnames():
    public_key_data, _ = generate_test_cert(
        hostname="foo", san_list=[x509.DNSName("bar"), x509.DNSName("baz")]
    )
    cert = load_certificate(public_key_data)
    assert cert.names == set(["foo", "bar", "baz"])

    for name in cert.names:
        assert cert.matches_name(name)


def test_wildcard_hostnames():
    public_key_data, _ = generate_test_cert(hostname="foo", san_list=[x509.DNSName("*.bar")])
    cert = load_certificate(public_key_data)
    assert cert.names == set(["foo", "*.bar"])

    for name in cert.names:
        assert cert.matches_name(name)

    assert cert.matches_name("something.bar")
    assert cert.matches_name("somethingelse.bar")
    assert cert.matches_name("cool.bar")
    assert not cert.matches_name("*")


def test_nondns_hostnames():
    public_key_data, _ = generate_test_cert(
        hostname="foo", san_list=[x509.UniformResourceIdentifier("yarg")]
    )
    cert = load_certificate(public_key_data)
    assert cert.names == set(["foo"])


def test_validate_private_key():
    public_key_data, private_key_data = generate_test_cert()

    private_key = NamedTemporaryFile(delete=True)
    private_key.write(private_key_data)
    private_key.seek(0)

    cert = load_certificate(public_key_data)
    cert.validate_private_key(private_key.name)


def test_invalid_private_key():
    public_key_data, _ = generate_test_cert()

    private_key = NamedTemporaryFile(delete=True)
    private_key.write(b"somerandomdata")
    private_key.seek(0)

    cert = load_certificate(public_key_data)
    with pytest.raises(KeyInvalidException):
        cert.validate_private_key(private_key.name)


def test_mismatch_private_key():
    public_key_data, _ = generate_test_cert()
    _, private_key_data = generate_test_cert()

    private_key = NamedTemporaryFile(delete=True)
    private_key.write(private_key_data)
    private_key.seek(0)

    cert = load_certificate(public_key_data)
    with pytest.raises(KeyInvalidException):
        cert.validate_private_key(private_key.name)
