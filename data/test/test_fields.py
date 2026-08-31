import base64
import pickle

import pytest
import resumablesha256

from data.fields import ResumableSHA256Field


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
