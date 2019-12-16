import json
import logging
import uuid

from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import datetime
from six import add_metaclass

from alembic import op
from sqlalchemy import text

from util.abchelpers import nooper

logger = logging.getLogger(__name__)


def escape_table_name(table_name):
    if op.get_bind().engine.name == "postgresql":
        # Needed for the `user` table.
        return '"%s"' % table_name

    return table_name


class DataTypes(object):
    @staticmethod
    def DateTime():
        return datetime.now()

    @staticmethod
    def Date():
        return datetime.now()

    @staticmethod
    def String():
        return "somestringvalue"

    @staticmethod
    def Token():
        return "%s%s" % ("a" * 60, "b" * 60)

    @staticmethod
    def UTF8Char():
        return "some other value"

    @staticmethod
    def UUID():
        return str(uuid.uuid4())

    @staticmethod
    def JSON():
        return json.dumps(dict(foo="bar", baz="meh"))

    @staticmethod
    def Boolean():
        if op.get_bind().engine.name == "postgresql":
            return True

        return 1

    @staticmethod
    def BigInteger():
        return 21474836470

    @staticmethod
    def Integer():
        return 42

    @staticmethod
    def Constant(value):
        def get_value():
            return value

        return get_value

    @staticmethod
    def Foreign(table_name):
        def get_index():
            result = op.get_bind().execute(
                "SELECT id FROM %s LIMIT 1" % escape_table_name(table_name)
            )
            try:
                return list(result)[0][0]
            except IndexError:
                raise Exception("Could not find row for table %s" % table_name)
            finally:
                result.close()

        return get_index


@add_metaclass(ABCMeta)
class MigrationTester(object):
    """
    Implements an interface for adding testing capabilities to the data model migration system in
    Alembic.
    """

    TestDataType = DataTypes

    @abstractmethod
    def is_testing(self):
        """
        Returns whether we are currently under a migration test.
        """

    @abstractmethod
    def populate_table(self, table_name, fields):
        """
        Called to populate a table with the given fields filled in with testing data.
        """

    @abstractmethod
    def populate_column(self, table_name, col_name, field_type):
        """
        Called to populate a column in a table to be filled in with testing data.
        """


@nooper
class NoopTester(MigrationTester):
    """
    No-op version of the tester, designed for production workloads.
    """


class PopulateTestDataTester(MigrationTester):
    def is_testing(self):
        return True

    def populate_table(self, table_name, fields):
        columns = {field_name: field_type() for field_name, field_type in fields}
        field_name_vars = [":" + field_name for field_name, _ in fields]

        if op.get_bind().engine.name == "postgresql":
            field_names = ["%s" % field_name for field_name, _ in fields]
        else:
            field_names = ["`%s`" % field_name for field_name, _ in fields]

        table_name = escape_table_name(table_name)
        query = text(
            "INSERT INTO %s (%s) VALUES (%s)"
            % (table_name, ", ".join(field_names), ", ".join(field_name_vars))
        )
        logger.info("Executing test query %s with values %s", query, list(columns.values()))
        op.get_bind().execute(query, **columns)

    def populate_column(self, table_name, col_name, field_type):
        col_value = field_type()
        row_id = DataTypes.Foreign(table_name)()

        table_name = escape_table_name(table_name)
        update_text = text("UPDATE %s SET %s=:col_value where ID=:row_id" % (table_name, col_name))
        logger.info(
            "Executing test query %s with value %s on row %s", update_text, col_value, row_id
        )
        op.get_bind().execute(update_text, col_value=col_value, row_id=row_id)
