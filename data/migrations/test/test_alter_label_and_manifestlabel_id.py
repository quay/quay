import importlib
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

migration = importlib.import_module(
    "data.migrations.versions.4e2713248cf9_alter_label_and_manifestlabel_id"
)


def _downgrade_values():
    return {
        "label_id": migration.INTEGER_MAX,
        "manifestlabel_id": migration.INTEGER_MAX,
        "manifestlabel_label_id": migration.INTEGER_MAX,
        "label_sequence": migration.INTEGER_MAX,
        "manifestlabel_sequence": migration.INTEGER_MAX,
    }


def _operations(values):
    result = Mock()
    result.mappings.return_value.one.return_value = values

    bind = Mock()
    bind.engine = SimpleNamespace(name="postgresql")
    bind.execute.return_value = result

    operations = Mock()
    operations.get_bind.return_value = bind
    return operations


@pytest.mark.parametrize(
    ("value_name", "display_name"),
    (
        ("label_id", "label.id"),
        ("manifestlabel_id", "manifestlabel.id"),
        ("manifestlabel_label_id", "manifestlabel.label_id"),
        ("label_sequence", "label_id_seq.last_value"),
        ("manifestlabel_sequence", "manifestlabel_id_seq.last_value"),
    ),
)
def test_downgrade_rejects_values_above_integer_max_before_altering_schema(
    value_name, display_name
):
    values = _downgrade_values()
    values[value_name] += 1
    operations = _operations(values)

    with pytest.raises(
        RuntimeError,
        match=re.escape(f"{display_name}={migration.INTEGER_MAX + 1}"),
    ):
        migration.downgrade(operations, None, None)

    operations.execute.assert_not_called()


def test_downgrade_accepts_values_at_integer_max():
    operations = _operations(_downgrade_values())

    migration.downgrade(operations, None, None)

    assert operations.execute.call_count == 7
