from app import app
from active_migration import ActiveDataMigration

if not app.config.get("SETUP_COMPLETE", False):
    print "head"
else:
    if ActiveDataMigration is not None:
        print ActiveDataMigration.alembic_migration_revision
    else:
        print "head"
