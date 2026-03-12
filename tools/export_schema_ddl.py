#!/usr/bin/env python3
"""Export Peewee models to SQLite DDL for Go consumption.

Usage: PYTHONPATH="." python tools/export_schema_ddl.py --output-dir internal/dal/schema/

This script uses the existing gen_sqlalchemy_metadata() function from
data/model/sqlalchemybridge.py to convert all Peewee models to SQLAlchemy
metadata, then renders CREATE TABLE / CREATE INDEX statements using the
SQLite dialect. It also replicates the seed data from initdb.py's
initialize_database() to produce INSERT statements for enum tables.

Run this whenever Peewee models change: make go-schema
CI validates that the committed .sql files match current models.
"""

import argparse
import os
import sys

from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from data.database import LEGACY_INDEX_MAP, all_models
from data.model.sqlalchemybridge import gen_sqlalchemy_metadata

# Seed data: replicated from initdb.py:initialize_database() to avoid
# importing initdb.py (which pulls in heavy deps like app, storage, etc.)
# CI's go-schema-check ensures this stays in sync with the Python models.
SEED_DATA = {
    "role": [
        {"name": "admin"},
        {"name": "write"},
        {"name": "read"},
    ],
    "teamrole": [
        {"name": "admin"},
        {"name": "creator"},
        {"name": "member"},
    ],
    "visibility": [
        {"name": "public"},
        {"name": "private"},
    ],
    "loginservice": [
        {"name": "google"},
        {"name": "github"},
        {"name": "quayrobot"},
        {"name": "ldap"},
        {"name": "jwtauthn"},
        {"name": "keystone"},
        {"name": "dex"},
        {"name": "oidc"},
    ],
    "buildtriggerservice": [
        {"name": "github"},
        {"name": "custom-git"},
        {"name": "bitbucket"},
        {"name": "gitlab"},
    ],
    "accesstokenkind": [
        {"name": "build-worker"},
        {"name": "pushpull-token"},
    ],
    "repositorykind": [
        {"name": "image"},
    ],
    "tagkind": [
        {"name": "tag"},
    ],
    "disablereason": [
        {"name": "user_toggled"},
        {"name": "successive_build_failures"},
        {"name": "successive_build_internal_errors"},
    ],
    "imagestoragelocation": [
        {"name": "local_eu"},
        {"name": "local_us"},
    ],
    "imagestoragetransformation": [
        {"name": "squash"},
        {"name": "aci"},
    ],
    "imagestoragesignaturekind": [
        {"name": "gpg2"},
    ],
    "labelsourcetype": [
        {"name": "manifest"},
        {"name": "api", "mutable": True},
        {"name": "internal"},
    ],
    "userpromptkind": [
        {"name": "confirm_username"},
        {"name": "enter_name"},
        {"name": "enter_company"},
    ],
    "quayregion": [
        {"name": "us"},
    ],
    "quayservice": [
        {"name": "quay"},
    ],
    "mediatype": [
        {"name": "text/plain"},
        {"name": "application/json"},
        {"name": "text/markdown"},
        # Docker Schema 1
        {"name": "application/vnd.docker.distribution.manifest.v1+json"},
        {"name": "application/vnd.docker.distribution.manifest.v1+prettyjws"},
        # Docker Schema 2
        {"name": "application/vnd.docker.distribution.manifest.v2+json"},
        {"name": "application/vnd.docker.distribution.manifest.list.v2+json"},
        # OCI
        {"name": "application/vnd.oci.image.manifest.v1+json"},
        {"name": "application/vnd.oci.image.index.v1+json"},
    ],
    "externalnotificationevent": [
        {"name": "repo_push"},
        {"name": "build_queued"},
        {"name": "build_start"},
        {"name": "build_success"},
        {"name": "build_cancelled"},
        {"name": "build_failure"},
        {"name": "vulnerability_found"},
        {"name": "repo_mirror_sync_started"},
        {"name": "repo_mirror_sync_success"},
        {"name": "repo_mirror_sync_failed"},
        {"name": "repo_image_expiry"},
    ],
    "externalnotificationmethod": [
        {"name": "quay_notification"},
        {"name": "email"},
        {"name": "webhook"},
        {"name": "flowdock"},
        {"name": "hipchat"},
        {"name": "slack"},
    ],
    "notificationkind": [
        {"name": "repo_push"},
        {"name": "build_queued"},
        {"name": "build_start"},
        {"name": "build_success"},
        {"name": "build_cancelled"},
        {"name": "build_failure"},
        {"name": "vulnerability_found"},
        {"name": "service_key_submitted"},
        {"name": "password_required"},
        {"name": "over_private_usage"},
        {"name": "expiring_license"},
        {"name": "maintenance"},
        {"name": "org_team_invite"},
        {"name": "repo_mirror_sync_started"},
        {"name": "repo_mirror_sync_success"},
        {"name": "repo_mirror_sync_failed"},
        {"name": "test_notification"},
        {"name": "quota_warning"},
        {"name": "quota_error"},
        {"name": "assigned_authorization"},
    ],
    "logentrykind": [
        {"name": "user_create"},
        {"name": "user_delete"},
        {"name": "user_disable"},
        {"name": "user_enable"},
        {"name": "user_change_email"},
        {"name": "user_change_password"},
        {"name": "user_change_name"},
        {"name": "user_change_invoicing"},
        {"name": "user_change_tag_expiration"},
        {"name": "user_change_metadata"},
        {"name": "user_generate_client_key"},
        {"name": "account_change_plan"},
        {"name": "account_change_cc"},
        {"name": "account_change_password"},
        {"name": "account_convert"},
        {"name": "create_robot"},
        {"name": "delete_robot"},
        {"name": "create_robot_federation"},
        {"name": "delete_robot_federation"},
        {"name": "federated_robot_token_exchange"},
        {"name": "create_repo"},
        {"name": "push_repo"},
        {"name": "push_repo_failed"},
        {"name": "pull_repo"},
        {"name": "pull_repo_failed"},
        {"name": "delete_repo"},
        {"name": "create_tag"},
        {"name": "move_tag"},
        {"name": "delete_tag"},
        {"name": "delete_tag_failed"},
        {"name": "revert_tag"},
        {"name": "add_repo_permission"},
        {"name": "change_repo_permission"},
        {"name": "delete_repo_permission"},
        {"name": "change_repo_visibility"},
        {"name": "change_repo_trust"},
        {"name": "add_repo_accesstoken"},
        {"name": "delete_repo_accesstoken"},
        {"name": "set_repo_description"},
        {"name": "change_repo_state"},
        {"name": "build_dockerfile"},
        {"name": "org_create"},
        {"name": "org_delete"},
        {"name": "org_create_team"},
        {"name": "org_delete_team"},
        {"name": "org_invite_team_member"},
        {"name": "org_delete_team_member_invite"},
        {"name": "org_add_team_member"},
        {"name": "org_team_member_invite_accepted"},
        {"name": "org_team_member_invite_declined"},
        {"name": "org_remove_team_member"},
        {"name": "org_set_team_description"},
        {"name": "org_set_team_role"},
        {"name": "org_change_email"},
        {"name": "org_change_invoicing"},
        {"name": "org_change_tag_expiration"},
        {"name": "org_change_name"},
        {"name": "create_prototype_permission"},
        {"name": "modify_prototype_permission"},
        {"name": "delete_prototype_permission"},
        {"name": "setup_repo_trigger"},
        {"name": "delete_repo_trigger"},
        {"name": "create_application"},
        {"name": "update_application"},
        {"name": "delete_application"},
        {"name": "reset_application_client_secret"},
        {"name": "add_repo_webhook"},
        {"name": "delete_repo_webhook"},
        {"name": "add_repo_notification"},
        {"name": "delete_repo_notification"},
        {"name": "reset_repo_notification"},
        {"name": "regenerate_robot_token"},
        {"name": "repo_verb"},
        {"name": "repo_mirror_enabled"},
        {"name": "repo_mirror_disabled"},
        {"name": "repo_mirror_config_changed"},
        {"name": "repo_mirror_sync_started"},
        {"name": "repo_mirror_sync_failed"},
        {"name": "repo_mirror_sync_success"},
        {"name": "repo_mirror_sync_now_requested"},
        {"name": "repo_mirror_sync_tag_success"},
        {"name": "repo_mirror_sync_tag_failed"},
        {"name": "repo_mirror_sync_test_success"},
        {"name": "repo_mirror_sync_test_failed"},
        {"name": "repo_mirror_sync_test_started"},
        {"name": "org_mirror_enabled"},
        {"name": "org_mirror_disabled"},
        {"name": "org_mirror_config_changed"},
        {"name": "org_mirror_sync_started"},
        {"name": "org_mirror_sync_failed"},
        {"name": "org_mirror_sync_success"},
        {"name": "org_mirror_sync_now_requested"},
        {"name": "org_mirror_sync_cancelled"},
        {"name": "org_mirror_repo_created"},
        {"name": "service_key_create"},
        {"name": "service_key_approve"},
        {"name": "service_key_delete"},
        {"name": "service_key_modify"},
        {"name": "service_key_extend"},
        {"name": "service_key_rotate"},
        {"name": "take_ownership"},
        {"name": "manifest_label_add"},
        {"name": "manifest_label_delete"},
        {"name": "change_tag_expiration"},
        {"name": "change_tag_immutability"},
        {"name": "toggle_repo_trigger"},
        {"name": "create_immutability_policy"},
        {"name": "update_immutability_policy"},
        {"name": "delete_immutability_policy"},
        {"name": "tag_made_immutable_by_policy"},
        {"name": "tags_made_immutable_by_policy"},
        {"name": "create_app_specific_token"},
        {"name": "revoke_app_specific_token"},
        {"name": "create_proxy_cache_config"},
        {"name": "delete_proxy_cache_config"},
        {"name": "start_build_trigger"},
        {"name": "cancel_build"},
        {"name": "login_success"},
        {"name": "login_failure"},
        {"name": "logout_success"},
        {"name": "permanently_delete_tag"},
        {"name": "autoprune_tag_delete"},
        {"name": "create_namespace_autoprune_policy"},
        {"name": "update_namespace_autoprune_policy"},
        {"name": "delete_namespace_autoprune_policy"},
        {"name": "create_repository_autoprune_policy"},
        {"name": "update_repository_autoprune_policy"},
        {"name": "delete_repository_autoprune_policy"},
        {"name": "enable_team_sync"},
        {"name": "disable_team_sync"},
        {"name": "oauth_token_assigned"},
        {"name": "oauth_token_revoked"},
        {"name": "export_logs_success"},
        {"name": "export_logs_failure"},
        {"name": "org_create_quota"},
        {"name": "org_change_quota"},
        {"name": "org_delete_quota"},
        {"name": "org_create_quota_limit"},
        {"name": "org_change_quota_limit"},
        {"name": "org_delete_quota_limit"},
    ],
}


def export_ddl(metadata, output_dir):
    """Export CREATE TABLE + CREATE INDEX statements to quay_schema.sql."""
    dialect = sqlite.dialect()
    lines = [
        "-- Auto-generated from Peewee models via tools/export_schema_ddl.py",
        "-- DO NOT EDIT - run 'make go-schema' to regenerate",
        "",
    ]

    for table in metadata.sorted_tables:
        ddl = CreateTable(table).compile(dialect=dialect)
        lines.append(str(ddl).strip() + ";")
        lines.append("")

    for table in metadata.sorted_tables:
        for index in table.indexes:
            try:
                idx_ddl = CreateIndex(index).compile(dialect=dialect)
                lines.append(str(idx_ddl).strip() + ";")
            except Exception:
                # Skip dialect-specific indexes (e.g. PostgreSQL GIN) that
                # can't compile under SQLite
                lines.append(
                    f"-- Skipped index {index.name} (not supported in SQLite)"
                )

    lines.append("")

    output_path = os.path.join(output_dir, "quay_schema.sql")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Written {output_path} ({len(metadata.sorted_tables)} tables)")


def export_seed_data(output_dir):
    """Export INSERT OR IGNORE statements for enum tables to seed_data.sql."""
    lines = [
        "-- Auto-generated from tools/export_schema_ddl.py SEED_DATA",
        "-- DO NOT EDIT - run 'make go-schema' to regenerate",
        "",
    ]

    for table_name, rows in SEED_DATA.items():
        lines.append(f"-- {table_name}")
        for row in rows:
            columns = ", ".join(row.keys())
            values = ", ".join(
                f"'{v}'" if isinstance(v, str) else str(int(v)) for v in row.values()
            )
            lines.append(
                f"INSERT OR IGNORE INTO {table_name} ({columns}) VALUES ({values});"
            )
        lines.append("")

    output_path = os.path.join(output_dir, "seed_data.sql")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    total_rows = sum(len(rows) for rows in SEED_DATA.values())
    print(
        f"Written {output_path} ({len(SEED_DATA)} tables, {total_rows} rows)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Export Peewee models to SQLite DDL for Go consumption"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write quay_schema.sql and seed_data.sql",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    metadata = gen_sqlalchemy_metadata(all_models, LEGACY_INDEX_MAP)
    export_ddl(metadata, args.output_dir)
    export_seed_data(args.output_dir)


if __name__ == "__main__":
    main()
