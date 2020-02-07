import pytest
from mock import patch

from data.runmigration import run_alembic_migration
from alembic.script import ScriptDirectory
from test.fixtures import *


@pytest.mark.parametrize(
    "db_uri, is_valid",
    [
        ("postgresql://devtable:password@quay-postgres/registry_database", True),
        ("postgresql://devtable:password%25@quay-postgres/registry_database", False),
        ("postgresql://devtable:password%%25@quay-postgres/registry_database", True),
        ("postgresql://devtable@db:password@quay-postgres/registry_database", True),
    ],
)
def test_alembic_db_uri(db_uri, is_valid):
    """
    Test if the given URI is escaped for string interpolation (Python's configparser).
    """
    with patch("alembic.script.ScriptDirectory.run_env") as m:
        if is_valid:
            run_alembic_migration(db_uri)
        else:
            with pytest.raises(ValueError):
                run_alembic_migration(db_uri)
