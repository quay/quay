from app import app
from active_migration import ActiveDataMigration


def current_migration():
    if not app.config.get("SETUP_COMPLETE", False):
        return "head"
    else:
        if ActiveDataMigration is not None:
            return ActiveDataMigration.alembic_migration_revision
        else:
            return "head"


def main():
    print(current_migration())


if __name__ == "__main__":
    main()
