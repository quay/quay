import importlib
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

migration = importlib.import_module(
    "data.migrations.versions.4e2713248cf9_alter_label_and_manifestlabel_id"
)

BIGINT_MAX = 9223372036854775807

UPGRADE_STATEMENTS = {
    "label.id": "ALTER TABLE label ALTER COLUMN id TYPE BIGINT;",
    "label_id_seq.type": "ALTER SEQUENCE label_id_seq AS BIGINT;",
    "label_id_seq.max": f"ALTER SEQUENCE label_id_seq MAXVALUE {BIGINT_MAX};",
    "manifestlabel.id": "ALTER TABLE manifestlabel ALTER COLUMN id TYPE BIGINT;",
    "manifestlabel_id_seq.type": "ALTER SEQUENCE manifestlabel_id_seq AS BIGINT;",
    "manifestlabel_id_seq.max": f"ALTER SEQUENCE manifestlabel_id_seq MAXVALUE {BIGINT_MAX};",
    "manifestlabel.label_id": "ALTER TABLE manifestlabel ALTER COLUMN label_id TYPE BIGINT;",
}


def _normalize_sql(statement):
    return " ".join(str(statement).split())


class FakePostgresSchema:
    """
    In-memory stand-in for the PostgreSQL catalog state read by the upgrade.

    No disposable PostgreSQL database is available to unit tests, so this models
    only what the migration inspects (column types via the inspector and
    pg_sequence rows via the bind) and applies the upgrade's DDL statements to
    that state. This lets tests assert both the emitted SQL and that re-running
    the upgrade against the resulting schema is a no-op.
    """

    def __init__(self, columns, sequences):
        self.columns = {table: dict(cols) for table, cols in columns.items()}
        self.sequences = {name: dict(state) for name, state in sequences.items()}
        self.executed = []
        self.sequence_lookups = []

        self.bind = Mock()
        self.bind.engine = SimpleNamespace(name="postgresql")
        self.bind.execute.side_effect = self._bind_execute

        self.operations = Mock()
        self.operations.get_bind.return_value = self.bind
        self.operations.execute.side_effect = self._op_execute

    def inspector(self):
        inspector = Mock()
        inspector.get_columns.side_effect = lambda table: [
            {"name": name, "type": column_type()}
            for name, column_type in self.columns[table].items()
        ]
        return inspector

    def _bind_execute(self, statement, params):
        sql = _normalize_sql(statement)
        assert "FROM pg_sequence" in sql
        assert "WHERE seqrelid = to_regclass(:sequence_name)" in sql
        name = params["sequence_name"]
        self.sequence_lookups.append(name)
        result = Mock()
        result.mappings.return_value.one.return_value = dict(self.sequences[name])
        return result

    def _op_execute(self, statement):
        sql = _normalize_sql(statement)
        self.executed.append(sql)
        for key, expected in UPGRADE_STATEMENTS.items():
            if sql == expected:
                target, attribute = key.split(".")
                if target in self.columns:
                    self.columns[target][attribute] = sa.BigInteger
                elif attribute == "type":
                    self.sequences[target]["data_type"] = "bigint"
                else:
                    self.sequences[target]["max_value"] = BIGINT_MAX
                return
        raise AssertionError(f"Unexpected statement executed by upgrade: {sql}")


def _integer_columns():
    return {
        "label": {"id": sa.Integer, "key": sa.String},
        "manifestlabel": {"id": sa.Integer, "label_id": sa.Integer, "manifest_id": sa.Integer},
    }


def _bigint_columns():
    return {
        "label": {"id": sa.BigInteger, "key": sa.String},
        "manifestlabel": {
            "id": sa.BigInteger,
            "label_id": sa.BigInteger,
            "manifest_id": sa.Integer,
        },
    }


def _integer_sequences():
    return {
        "label_id_seq": {"data_type": "integer", "max_value": migration.INTEGER_MAX},
        "manifestlabel_id_seq": {"data_type": "integer", "max_value": migration.INTEGER_MAX},
    }


def _bigint_sequences():
    return {
        "label_id_seq": {"data_type": "bigint", "max_value": BIGINT_MAX},
        "manifestlabel_id_seq": {"data_type": "bigint", "max_value": BIGINT_MAX},
    }


@pytest.fixture
def run_upgrade(monkeypatch):
    def run(schema):
        monkeypatch.setattr(
            migration.Inspector, "from_engine", lambda bind: schema.inspector(), raising=True
        )
        schema.executed.clear()
        schema.sequence_lookups.clear()
        migration.upgrade(schema.operations, None, None)
        return schema.executed

    return run


def _assert_fully_migrated(schema):
    assert schema.columns["label"]["id"] is sa.BigInteger
    assert schema.columns["manifestlabel"]["id"] is sa.BigInteger
    assert schema.columns["manifestlabel"]["label_id"] is sa.BigInteger
    for name, state in schema.sequences.items():
        assert state["data_type"].lower() == "bigint", name
        assert state["max_value"] == BIGINT_MAX, name


def test_upgrade_from_integer_schema_widens_columns_and_sequences(run_upgrade):
    schema = FakePostgresSchema(_integer_columns(), _integer_sequences())

    executed = run_upgrade(schema)

    assert executed == [
        UPGRADE_STATEMENTS["label.id"],
        UPGRADE_STATEMENTS["label_id_seq.type"],
        UPGRADE_STATEMENTS["label_id_seq.max"],
        UPGRADE_STATEMENTS["manifestlabel.id"],
        UPGRADE_STATEMENTS["manifestlabel_id_seq.type"],
        UPGRADE_STATEMENTS["manifestlabel_id_seq.max"],
        UPGRADE_STATEMENTS["manifestlabel.label_id"],
    ]
    assert schema.sequence_lookups == ["label_id_seq", "manifestlabel_id_seq"]
    # Unrelated columns are never altered.
    assert schema.columns["manifestlabel"]["manifest_id"] is sa.Integer
    _assert_fully_migrated(schema)


def test_upgrade_is_idempotent_when_rerun(run_upgrade):
    schema = FakePostgresSchema(_integer_columns(), _integer_sequences())

    assert len(run_upgrade(schema)) == len(UPGRADE_STATEMENTS)
    assert run_upgrade(schema) == []
    _assert_fully_migrated(schema)


def test_upgrade_on_already_migrated_schema_executes_nothing(run_upgrade):
    schema = FakePostgresSchema(_bigint_columns(), _bigint_sequences())

    assert run_upgrade(schema) == []
    # Sequence state is still checked independently of the column types.
    assert schema.sequence_lookups == ["label_id_seq", "manifestlabel_id_seq"]


@pytest.mark.parametrize(
    ("columns", "sequences", "expected_keys"),
    (
        pytest.param(
            _bigint_columns(),
            _integer_sequences(),
            [
                "label_id_seq.type",
                "label_id_seq.max",
                "manifestlabel_id_seq.type",
                "manifestlabel_id_seq.max",
            ],
            id="columns-bigint-sequences-integer",
        ),
        pytest.param(
            {
                "label": {"id": sa.BigInteger},
                "manifestlabel": {"id": sa.Integer, "label_id": sa.Integer},
            },
            {
                "label_id_seq": {"data_type": "bigint", "max_value": BIGINT_MAX},
                "manifestlabel_id_seq": {
                    "data_type": "integer",
                    "max_value": migration.INTEGER_MAX,
                },
            },
            [
                "manifestlabel.id",
                "manifestlabel_id_seq.type",
                "manifestlabel_id_seq.max",
                "manifestlabel.label_id",
            ],
            id="label-done-manifestlabel-pending",
        ),
        pytest.param(
            {
                "label": {"id": sa.BigInteger},
                "manifestlabel": {"id": sa.BigInteger, "label_id": sa.Integer},
            },
            _bigint_sequences(),
            ["manifestlabel.label_id"],
            id="only-foreign-key-column-pending",
        ),
        pytest.param(
            _bigint_columns(),
            {
                "label_id_seq": {"data_type": "bigint", "max_value": migration.INTEGER_MAX},
                "manifestlabel_id_seq": {"data_type": "BIGINT", "max_value": BIGINT_MAX},
            },
            ["label_id_seq.max"],
            id="sequence-type-bigint-but-integer-maxvalue",
        ),
    ),
)
def test_upgrade_handles_partially_migrated_schema(run_upgrade, columns, sequences, expected_keys):
    schema = FakePostgresSchema(columns, sequences)

    executed = run_upgrade(schema)

    assert executed == [UPGRADE_STATEMENTS[key] for key in expected_keys]
    _assert_fully_migrated(schema)
    assert run_upgrade(schema) == []


def test_upgrade_is_noop_on_non_postgresql_database():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table("label", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table(
        "manifestlabel",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label_id", sa.Integer(), sa.ForeignKey("label.id"), nullable=False),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(sa.text("INSERT INTO label (id) VALUES (1)"))
        connection.execute(sa.text("INSERT INTO manifestlabel (id, label_id) VALUES (1, 1)"))
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})

        migration.upgrade(Operations(context), None, None)

        inspector = sa.inspect(connection)
        for table, column in (
            ("label", "id"),
            ("manifestlabel", "id"),
            ("manifestlabel", "label_id"),
        ):
            column_type = next(
                c["type"] for c in inspector.get_columns(table) if c["name"] == column
            )
            assert isinstance(column_type, sa.Integer)
            assert not isinstance(column_type, sa.BigInteger)
        assert connection.execute(sa.text("SELECT label_id FROM manifestlabel")).scalar() == 1


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
