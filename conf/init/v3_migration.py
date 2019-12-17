from app import app
from active_migration import ActiveDataMigration

if not app.config.get("SETUP_COMPLETE", False):
    print("head")
else:
    v3_upgrade_mode = app.config.get("V3_UPGRADE_MODE")
    if v3_upgrade_mode == "background":
        raise Exception(
            'V3_UPGRADE_MODE must be "complete". This requires a full upgrade to Quay:v3.0. See https://access.qa.redhat.com/documentation/en-us/red_hat_quay/3/html/upgrade_quay/index'
        )
    elif v3_upgrade_mode == "production-transition":
        print("481623ba00ba")
    elif (
        v3_upgrade_mode == "post-oci-rollout"
        or v3_upgrade_mode == "post-oci-roll-back-compat"
        or v3_upgrade_mode == "complete"
    ):
        if ActiveDataMigration is not None:
            print(ActiveDataMigration.alembic_migration_revision)
        else:
            print("head")
    else:
        raise Exception("Unknown V3_UPGRADE_MODE: %s" % v3_upgrade_mode)
