""" DBA Operator Migration Generator

This module supports instrumenting, harvesting, and writing migrations for the
[DBA operator](https://github.com/quay/dba-operator) from the Alembic migrations.
The module generates instances of the `databasemigration` Kubernetes custom resource,
which defines the parameters for synthesizing a Kubernetes job to connect to and
migrate a relational database.
"""

import yaml
import logging

from functools import partial, wraps
from alembic.operations import ops

import sqlalchemy as sa


logger = logging.getLogger(__name__)


class Migration(object):
    def __init__(self):
        self._schema_hints = []

    def dump_yaml_and_reset(self, stream, revision, down_revision):
        migration_object = {
            "apiVersion": "dbaoperator.app-sre.redhat.com/v1alpha1",
            "kind": "DatabaseMigration",
            "metadata": {
                "name": revision,
            },
            "spec": {
                "previous": down_revision,
                "migrationContainerSpec": {
                    "name": revision,
                    "image": "quay.io/quay/quay",
                    "command": [
                        "/quay-registry/quay-entrypoint.sh",
                        "migrate",
                        revision,
                    ],
                },
                "schemaHints": self._schema_hints,
            },
        }
        yaml.dump(migration_object, stream)
        self._schema_hints = []

    def add_hints_from_ops(self, directive):
        for op in directive.ops:
            if isinstance(op, ops.ModifyTableOps):
                for subop in op.ops:
                    if isinstance(subop, ops.AddColumnOp):
                        self.hint_add_column(subop.table_name, subop.column)
                    elif isinstance(subop, ops.CreateIndexOp):
                        self.hint_create_index(
                            subop.index_name,
                            subop.table_name,
                            subop.columns,
                            subop.unique,
                        )
                    elif isinstance(subop, ops.DropIndexOp):
                        self.hint_drop_index(subop.index_name, subop.table_name)
                    else:
                        logger.debug("Skipping migration operation: %s", subop.__class__)
            elif isinstance(op, ops.DropTableOp):
                self.hint_drop_table(op.table_name)
            elif isinstance(op, ops.CreateTableOp):
                self.hint_create_table(op.table_name, *op.columns)
            else:
                logger.debug("Skipping migration operation: %s", op.__class__)

    def _format_column_hint(self, column):
        return {
            "name": column.name,
            "nullable": column.nullable,
        }

    def _format_column_list_hint(self, columns):
        return [
            self._format_column_hint(column) for column in columns if isinstance(column, sa.Column)
        ]

    def hint_create_table(self, table_name, *columns, **kwargs):
        self._schema_hints.append(
            {
                "operation": "createTable",
                "table": table_name,
                "columns": self._format_column_list_hint(columns),
            }
        )

    def hint_drop_table(self, table_name, **kwargs):
        self._schema_hints.append(
            {
                "operation": "dropTable",
                "table": table_name,
            }
        )

    def hint_add_column(self, table_name, column, *args, **kwargs):
        self._schema_hints.append(
            {
                "operation": "addColumn",
                "table": table_name,
                "columns": [self._format_column_hint(column)],
            }
        )

    def hint_create_index(self, index_name, table_name, columns, unique=False, **kwargs):
        self._schema_hints.append(
            {
                "operation": "createIndex",
                "table": table_name,
                "indexType": "unique" if unique else "index",
                "indexName": index_name,
                "columns": self._format_column_list_hint(columns),
            }
        )

    def hint_drop_index(self, index_name, table_name, **kwargs):
        self._schema_hints.append(
            {
                "operation": "dropIndex",
                "table": table_name,
                "indexName": index_name,
            }
        )


class OpLogger(object):
    def __init__(self, delegate_module, migration):
        self._delegate_module = delegate_module

        self._collectors = {
            "add_column": partial(migration.hint_add_column),
            "create_table": partial(migration.hint_create_table),
            "drop_table": partial(migration.hint_drop_table),
            "create_index": partial(migration.hint_create_index),
            "drop_index": partial(migration.hint_drop_index),
        }

    def __getattr__(self, attr_name):
        # Will raise proper attribute error
        maybe_callable = self._delegate_module.__dict__[attr_name]
        if callable(maybe_callable) and attr_name in self._collectors:
            # Build a callable which when executed places the request
            # onto a queue
            collector = self._collectors[attr_name]

            @wraps(maybe_callable)
            def wrapped_method(*args, **kwargs):
                result = maybe_callable(*args, **kwargs)
                collector(*args, **kwargs)
                return result

            return wrapped_method
        return maybe_callable


def _quoted_string_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.add_representer(sa.sql.elements.quoted_name, _quoted_string_representer)
