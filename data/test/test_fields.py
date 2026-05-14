import base64
import pickle

import pytest
import resumablesha256

from data.fields import _ALLOWED_UNPICKLE_CLASSES, ResumableSHA256Field


def _can_import(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def test_resumable_sha256_field_roundtrip():
    field = ResumableSHA256Field()
    hasher = resumablesha256.sha256()
    hasher.update(b"hello world")

    db_val = field.db_value(hasher)
    restored = field.python_value(db_val)

    assert restored.hexdigest() == hasher.hexdigest()


def test_resumable_sha256_field_rejects_malicious_payload():
    """Verify that arbitrary classes cannot be deserialized (CVE-2026-32590)."""
    field = ResumableSHA256Field()

    class Exploit:
        def __reduce__(self):
            import os

            return (os.system, ("echo pwned",))

    malicious = base64.b64encode(pickle.dumps(Exploit())).decode("ascii")

    with pytest.raises(pickle.UnpicklingError, match="Forbidden class"):
        field.python_value(malicious)


@pytest.mark.skipif(
    not _can_import("resumablehash"),
    reason="resumablehash not yet published to PyPI",
)
def test_safe_unpickler_allows_resumablehash_sha384():
    """Verify that resumablehash.sha384 objects can be deserialized via the allowlist."""
    import resumablehash

    field = ResumableSHA256Field()
    hasher = resumablehash.sha384()
    hasher.update(b"test data for sha384")

    db_val = field.db_value(hasher)
    restored = field.python_value(db_val)

    assert restored.hexdigest() == hasher.hexdigest()


@pytest.mark.skipif(
    not _can_import("resumablehash"),
    reason="resumablehash not yet published to PyPI",
)
def test_safe_unpickler_allows_resumablehash_sha512():
    """Verify that resumablehash.sha512 objects can be deserialized via the allowlist."""
    import resumablehash

    field = ResumableSHA256Field()
    hasher = resumablehash.sha512()
    hasher.update(b"test data for sha512")

    db_val = field.db_value(hasher)
    restored = field.python_value(db_val)

    assert restored.hexdigest() == hasher.hexdigest()


def test_safe_unpickler_still_allows_legacy_sha256():
    """Verify that the legacy resumablesha256.sha256 class still deserializes correctly."""
    field = ResumableSHA256Field()
    hasher = resumablesha256.sha256()
    hasher.update(b"legacy sha256 data")

    db_val = field.db_value(hasher)
    restored = field.python_value(db_val)

    assert restored.hexdigest() == hasher.hexdigest()


def test_safe_unpickler_rejects_arbitrary_class():
    """Security regression: arbitrary non-hash classes must be rejected."""
    field = ResumableSHA256Field()

    class ArbitraryClass:
        def __reduce__(self):
            return (eval, ("1+1",))

    malicious = base64.b64encode(pickle.dumps(ArbitraryClass())).decode("ascii")

    with pytest.raises(pickle.UnpicklingError, match="Forbidden class"):
        field.python_value(malicious)


def test_allowed_unpickle_classes_is_frozenset():
    """Verify the allowlist is a frozenset (immutable at runtime)."""
    assert isinstance(_ALLOWED_UNPICKLE_CLASSES, frozenset)
