import base64
import pickle

import pytest
import resumablesha256

from data.fields import JSONField, ResumableSHA256Field


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


class TestJSONField:
    def test_python_value_returns_dict_passthrough(self):
        field = JSONField()
        value = {"key": "val"}
        assert field.python_value(value) is value

    def test_python_value_returns_list_passthrough(self):
        field = JSONField()
        value = [1, 2, 3]
        assert field.python_value(value) is value

    def test_python_value_parses_json_string(self):
        field = JSONField()
        assert field.python_value('{"a": 1}') == {"a": 1}

    def test_python_value_returns_empty_dict_for_none(self):
        field = JSONField()
        assert field.python_value(None) == {}

    def test_python_value_returns_empty_dict_for_empty_string(self):
        field = JSONField()
        assert field.python_value("") == {}
