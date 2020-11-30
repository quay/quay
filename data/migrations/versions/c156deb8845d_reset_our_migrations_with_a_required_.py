"""
Reset our migrations with a required update.

Revision ID: c156deb8845d
Revises: None
Create Date: 2016-11-08 11:58:11.110762
"""

# revision identifiers, used by Alembic.
revision = "c156deb8845d"
down_revision = None

import sqlalchemy as sa
from util.migrate import UTF8LongText, UTF8CharField
from datetime import datetime


def upgrade(op, tables, tester):
    now = datetime.now().strftime("'%Y-%m-%d %H:%M:%S'")

    op.create_table(
        "accesstokenkind",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accesstokenkind")),
    )
    op.create_index("accesstokenkind_name", "accesstokenkind", ["name"], unique=True)
    op.create_table(
        "buildtriggerservice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buildtriggerservice")),
    )
    op.create_index("buildtriggerservice_name", "buildtriggerservice", ["name"], unique=True)
    op.create_table(
        "externalnotificationevent",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_externalnotificationevent")),
    )
    op.create_index(
        "externalnotificationevent_name", "externalnotificationevent", ["name"], unique=True
    )
    op.create_table(
        "externalnotificationmethod",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_externalnotificationmethod")),
    )
    op.create_index(
        "externalnotificationmethod_name", "externalnotificationmethod", ["name"], unique=True
    )
    op.create_table(
        "imagestorage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("image_size", sa.BigInteger(), nullable=True),
        sa.Column("uncompressed_size", sa.BigInteger(), nullable=True),
        sa.Column("uploading", sa.Boolean(), nullable=True),
        sa.Column(
            "cas_path", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.Column("content_checksum", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imagestorage")),
    )
    op.create_index(
        "imagestorage_content_checksum", "imagestorage", ["content_checksum"], unique=False
    )
    op.create_index("imagestorage_uuid", "imagestorage", ["uuid"], unique=True)
    op.create_table(
        "imagestoragelocation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imagestoragelocation")),
    )
    op.create_index("imagestoragelocation_name", "imagestoragelocation", ["name"], unique=True)
    op.create_table(
        "imagestoragesignaturekind",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imagestoragesignaturekind")),
    )
    op.create_index(
        "imagestoragesignaturekind_name", "imagestoragesignaturekind", ["name"], unique=True
    )
    op.create_table(
        "imagestoragetransformation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imagestoragetransformation")),
    )
    op.create_index(
        "imagestoragetransformation_name", "imagestoragetransformation", ["name"], unique=True
    )
    op.create_table(
        "labelsourcetype",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mutable", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labelsourcetype")),
    )
    op.create_index("labelsourcetype_name", "labelsourcetype", ["name"], unique=True)
    op.create_table(
        "logentrykind",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_logentrykind")),
    )
    op.create_index("logentrykind_name", "logentrykind", ["name"], unique=True)
    op.create_table(
        "loginservice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loginservice")),
    )
    op.create_index("loginservice_name", "loginservice", ["name"], unique=True)
    op.create_table(
        "mediatype",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mediatype")),
    )
    op.create_index("mediatype_name", "mediatype", ["name"], unique=True)
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_table(
        "notificationkind",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notificationkind")),
    )
    op.create_index("notificationkind_name", "notificationkind", ["name"], unique=True)
    op.create_table(
        "quayregion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quayregion")),
    )
    op.create_index("quayregion_name", "quayregion", ["name"], unique=True)
    op.create_table(
        "quayservice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quayservice")),
    )
    op.create_index("quayservice_name", "quayservice", ["name"], unique=True)
    op.create_table(
        "queueitem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("queue_name", sa.String(length=1024), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("available_after", sa.DateTime(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("processing_expires", sa.DateTime(), nullable=True),
        sa.Column("retries_remaining", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queueitem")),
    )
    op.create_index("queueitem_available", "queueitem", ["available"], unique=False)
    op.create_index("queueitem_available_after", "queueitem", ["available_after"], unique=False)
    op.create_index(
        "queueitem_processing_expires", "queueitem", ["processing_expires"], unique=False
    )
    op.create_index(
        "queueitem_queue_name", "queueitem", ["queue_name"], unique=False, mysql_length=767
    )
    op.create_index("queueitem_retries_remaining", "queueitem", ["retries_remaining"], unique=False)
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role")),
    )
    op.create_index("role_name", "role", ["name"], unique=True)
    op.create_table(
        "servicekeyapproval",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("approval_type", sa.String(length=255), nullable=False),
        sa.Column("approved_date", sa.DateTime(), nullable=False),
        sa.Column("notes", UTF8LongText(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_servicekeyapproval")),
    )
    op.create_index(
        "servicekeyapproval_approval_type", "servicekeyapproval", ["approval_type"], unique=False
    )
    op.create_index(
        "servicekeyapproval_approver_id", "servicekeyapproval", ["approver_id"], unique=False
    )
    op.create_table(
        "teamrole",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teamrole")),
    )
    op.create_index("teamrole_name", "teamrole", ["name"], unique=False)
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=True),
        sa.Column("organization", sa.Boolean(), nullable=False),
        sa.Column("robot", sa.Boolean(), nullable=False),
        sa.Column("invoice_email", sa.Boolean(), nullable=False),
        sa.Column("invalid_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_invalid_login", sa.DateTime(), nullable=False),
        sa.Column(
            "removed_tag_expiration_s", sa.Integer(), nullable=False, server_default="1209600"
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column("invoice_email_address", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
    )
    op.create_index("user_email", "user", ["email"], unique=True)
    op.create_index("user_invoice_email_address", "user", ["invoice_email_address"], unique=False)
    op.create_index("user_organization", "user", ["organization"], unique=False)
    op.create_index("user_robot", "user", ["robot"], unique=False)
    op.create_index("user_stripe_id", "user", ["stripe_id"], unique=False)
    op.create_index("user_username", "user", ["username"], unique=True)
    op.create_table(
        "visibility",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visibility")),
    )
    op.create_index("visibility_name", "visibility", ["name"], unique=True)
    op.create_table(
        "emailconfirmation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("pw_reset", sa.Boolean(), nullable=False),
        sa.Column("new_email", sa.String(length=255), nullable=True),
        sa.Column("email_confirm", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_emailconfirmation_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emailconfirmation")),
    )
    op.create_index("emailconfirmation_code", "emailconfirmation", ["code"], unique=True)
    op.create_index("emailconfirmation_user_id", "emailconfirmation", ["user_id"], unique=False)
    op.create_table(
        "federatedlogin",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("service_ident", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["loginservice.id"],
            name=op.f("fk_federatedlogin_service_id_loginservice"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_federatedlogin_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_federatedlogin")),
    )
    op.create_index("federatedlogin_service_id", "federatedlogin", ["service_id"], unique=False)
    op.create_index(
        "federatedlogin_service_id_service_ident",
        "federatedlogin",
        ["service_id", "service_ident"],
        unique=True,
    )
    op.create_index(
        "federatedlogin_service_id_user_id",
        "federatedlogin",
        ["service_id", "user_id"],
        unique=True,
    )
    op.create_index("federatedlogin_user_id", "federatedlogin", ["user_id"], unique=False)
    op.create_table(
        "imagestorageplacement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["imagestoragelocation.id"],
            name=op.f("fk_imagestorageplacement_location_id_imagestoragelocation"),
        ),
        sa.ForeignKeyConstraint(
            ["storage_id"],
            ["imagestorage.id"],
            name=op.f("fk_imagestorageplacement_storage_id_imagestorage"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imagestorageplacement")),
    )
    op.create_index(
        "imagestorageplacement_location_id", "imagestorageplacement", ["location_id"], unique=False
    )
    op.create_index(
        "imagestorageplacement_storage_id", "imagestorageplacement", ["storage_id"], unique=False
    )
    op.create_index(
        "imagestorageplacement_storage_id_location_id",
        "imagestorageplacement",
        ["storage_id", "location_id"],
        unique=True,
    )
    op.create_table(
        "imagestoragesignature",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_id", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("uploading", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["kind_id"],
            ["imagestoragesignaturekind.id"],
            name=op.f("fk_imagestoragesignature_kind_id_imagestoragesignaturekind"),
        ),
        sa.ForeignKeyConstraint(
            ["storage_id"],
            ["imagestorage.id"],
            name=op.f("fk_imagestoragesignature_storage_id_imagestorage"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imagestoragesignature")),
    )
    op.create_index(
        "imagestoragesignature_kind_id", "imagestoragesignature", ["kind_id"], unique=False
    )
    op.create_index(
        "imagestoragesignature_kind_id_storage_id",
        "imagestoragesignature",
        ["kind_id", "storage_id"],
        unique=True,
    )
    op.create_index(
        "imagestoragesignature_storage_id", "imagestoragesignature", ["storage_id"], unique=False
    )
    op.create_table(
        "label",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("key", UTF8CharField(length=255), nullable=False),
        sa.Column("value", UTF8LongText(), nullable=False),
        sa.Column("media_type_id", sa.Integer(), nullable=False),
        sa.Column("source_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_type_id"], ["mediatype.id"], name=op.f("fk_label_media_type_id_mediatype")
        ),
        sa.ForeignKeyConstraint(
            ["source_type_id"],
            ["labelsourcetype.id"],
            name=op.f("fk_label_source_type_id_labelsourcetype"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_label")),
    )
    op.create_index("label_key", "label", ["key"], unique=False)
    op.create_index("label_media_type_id", "label", ["media_type_id"], unique=False)
    op.create_index("label_source_type_id", "label", ["source_type_id"], unique=False)
    op.create_index("label_uuid", "label", ["uuid"], unique=True)
    op.create_table(
        "logentry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("performer_id", sa.Integer(), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=True),
        sa.Column("datetime", sa.DateTime(), nullable=False),
        sa.Column("ip", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["kind_id"], ["logentrykind.id"], name=op.f("fk_logentry_kind_id_logentrykind")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_logentry")),
    )
    op.create_index("logentry_account_id", "logentry", ["account_id"], unique=False)
    op.create_index(
        "logentry_account_id_datetime", "logentry", ["account_id", "datetime"], unique=False
    )
    op.create_index("logentry_datetime", "logentry", ["datetime"], unique=False)
    op.create_index("logentry_kind_id", "logentry", ["kind_id"], unique=False)
    op.create_index("logentry_performer_id", "logentry", ["performer_id"], unique=False)
    op.create_index(
        "logentry_performer_id_datetime", "logentry", ["performer_id", "datetime"], unique=False
    )
    op.create_index("logentry_repository_id", "logentry", ["repository_id"], unique=False)
    op.create_index(
        "logentry_repository_id_datetime", "logentry", ["repository_id", "datetime"], unique=False
    )
    op.create_index(
        "logentry_repository_id_datetime_kind_id",
        "logentry",
        ["repository_id", "datetime", "kind_id"],
        unique=False,
    )
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("dismissed", sa.Boolean(), nullable=False),
        sa.Column("lookup_path", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["kind_id"],
            ["notificationkind.id"],
            name=op.f("fk_notification_kind_id_notificationkind"),
        ),
        sa.ForeignKeyConstraint(
            ["target_id"], ["user.id"], name=op.f("fk_notification_target_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification")),
    )
    op.create_index("notification_created", "notification", ["created"], unique=False)
    op.create_index("notification_kind_id", "notification", ["kind_id"], unique=False)
    op.create_index("notification_lookup_path", "notification", ["lookup_path"], unique=False)
    op.create_index("notification_target_id", "notification", ["target_id"], unique=False)
    op.create_index("notification_uuid", "notification", ["uuid"], unique=False)
    op.create_table(
        "oauthapplication",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=255), nullable=False),
        sa.Column("redirect_uri", sa.String(length=255), nullable=False),
        sa.Column("application_uri", sa.String(length=255), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("gravatar_email", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["user.id"], name=op.f("fk_oauthapplication_organization_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauthapplication")),
    )
    op.create_index("oauthapplication_client_id", "oauthapplication", ["client_id"], unique=False)
    op.create_index(
        "oauthapplication_organization_id", "oauthapplication", ["organization_id"], unique=False
    )
    op.create_table(
        "quayrelease",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=255), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("reverted", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["region_id"], ["quayregion.id"], name=op.f("fk_quayrelease_region_id_quayregion")
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["quayservice.id"], name=op.f("fk_quayrelease_service_id_quayservice")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quayrelease")),
    )
    op.create_index("quayrelease_created", "quayrelease", ["created"], unique=False)
    op.create_index("quayrelease_region_id", "quayrelease", ["region_id"], unique=False)
    op.create_index("quayrelease_service_id", "quayrelease", ["service_id"], unique=False)
    op.create_index(
        "quayrelease_service_id_region_id_created",
        "quayrelease",
        ["service_id", "region_id", "created"],
        unique=False,
    )
    op.create_index(
        "quayrelease_service_id_version_region_id",
        "quayrelease",
        ["service_id", "version", "region_id"],
        unique=True,
    )
    op.create_table(
        "repository",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("namespace_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("visibility_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("badge_token", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["namespace_user_id"], ["user.id"], name=op.f("fk_repository_namespace_user_id_user")
        ),
        sa.ForeignKeyConstraint(
            ["visibility_id"],
            ["visibility.id"],
            name=op.f("fk_repository_visibility_id_visibility"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repository")),
    )
    op.create_index(
        "repository_namespace_user_id", "repository", ["namespace_user_id"], unique=False
    )
    op.create_index(
        "repository_namespace_user_id_name",
        "repository",
        ["namespace_user_id", "name"],
        unique=True,
    )
    op.create_index("repository_visibility_id", "repository", ["visibility_id"], unique=False)
    op.create_table(
        "servicekey",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kid", sa.String(length=255), nullable=False),
        sa.Column("service", sa.String(length=255), nullable=False),
        sa.Column("jwk", UTF8LongText(), nullable=False),
        sa.Column("metadata", UTF8LongText(), nullable=False),
        sa.Column("created_date", sa.DateTime(), nullable=False),
        sa.Column("expiration_date", sa.DateTime(), nullable=True),
        sa.Column("rotation_duration", sa.Integer(), nullable=True),
        sa.Column("approval_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["servicekeyapproval.id"],
            name=op.f("fk_servicekey_approval_id_servicekeyapproval"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_servicekey")),
    )
    op.create_index("servicekey_approval_id", "servicekey", ["approval_id"], unique=False)
    op.create_index("servicekey_kid", "servicekey", ["kid"], unique=True)
    op.create_index("servicekey_service", "servicekey", ["service"], unique=False)
    op.create_table(
        "team",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["user.id"], name=op.f("fk_team_organization_id_user")
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["teamrole.id"], name=op.f("fk_team_role_id_teamrole")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_team")),
    )
    op.create_index("team_name", "team", ["name"], unique=False)
    op.create_index("team_name_organization_id", "team", ["name", "organization_id"], unique=True)
    op.create_index("team_organization_id", "team", ["organization_id"], unique=False)
    op.create_index("team_role_id", "team", ["role_id"], unique=False)
    op.create_table(
        "torrentinfo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_id", sa.Integer(), nullable=False),
        sa.Column("piece_length", sa.Integer(), nullable=False),
        sa.Column("pieces", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["storage_id"], ["imagestorage.id"], name=op.f("fk_torrentinfo_storage_id_imagestorage")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_torrentinfo")),
    )
    op.create_index("torrentinfo_storage_id", "torrentinfo", ["storage_id"], unique=False)
    op.create_index(
        "torrentinfo_storage_id_piece_length",
        "torrentinfo",
        ["storage_id", "piece_length"],
        unique=True,
    )
    op.create_table(
        "userregion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["imagestoragelocation.id"],
            name=op.f("fk_userregion_location_id_imagestoragelocation"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_userregion_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_userregion")),
    )
    op.create_index("userregion_location_id", "userregion", ["location_id"], unique=False)
    op.create_index("userregion_user_id", "userregion", ["user_id"], unique=False)
    op.create_table(
        "accesstoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("friendly_name", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("temporary", sa.Boolean(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["kind_id"], ["accesstokenkind.id"], name=op.f("fk_accesstoken_kind_id_accesstokenkind")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_accesstoken_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], name=op.f("fk_accesstoken_role_id_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accesstoken")),
    )
    op.create_index("accesstoken_code", "accesstoken", ["code"], unique=True)
    op.create_index("accesstoken_kind_id", "accesstoken", ["kind_id"], unique=False)
    op.create_index("accesstoken_repository_id", "accesstoken", ["repository_id"], unique=False)
    op.create_index("accesstoken_role_id", "accesstoken", ["role_id"], unique=False)
    op.create_table(
        "blobupload",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("sha_state", sa.Text(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("storage_metadata", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uncompressed_byte_count", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False, server_default=sa.text(now)),
        sa.Column("piece_sha_state", UTF8LongText(), nullable=True),
        sa.Column("piece_hashes", UTF8LongText(), nullable=True),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["imagestoragelocation.id"],
            name=op.f("fk_blobupload_location_id_imagestoragelocation"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_blobupload_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blobupload")),
    )
    op.create_index("blobupload_created", "blobupload", ["created"], unique=False)
    op.create_index("blobupload_location_id", "blobupload", ["location_id"], unique=False)
    op.create_index("blobupload_repository_id", "blobupload", ["repository_id"], unique=False)
    op.create_index(
        "blobupload_repository_id_uuid", "blobupload", ["repository_id", "uuid"], unique=True
    )
    op.create_index("blobupload_uuid", "blobupload", ["uuid"], unique=True)
    op.create_table(
        "image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("docker_image_id", sa.String(length=255), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("ancestors", sa.String(length=60535), nullable=True),
        sa.Column("storage_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("comment", UTF8LongText(), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("aggregate_size", sa.BigInteger(), nullable=True),
        sa.Column("v1_json_metadata", UTF8LongText(), nullable=True),
        sa.Column("v1_checksum", sa.String(length=255), nullable=True),
        sa.Column(
            "security_indexed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
        sa.Column("security_indexed_engine", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repository.id"], name=op.f("fk_image_repository_id_repository")
        ),
        sa.ForeignKeyConstraint(
            ["storage_id"], ["imagestorage.id"], name=op.f("fk_image_storage_id_imagestorage")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_image")),
    )
    op.create_index("image_ancestors", "image", ["ancestors"], unique=False, mysql_length=767)
    op.create_index("image_docker_image_id", "image", ["docker_image_id"], unique=False)
    op.create_index("image_parent_id", "image", ["parent_id"], unique=False)
    op.create_index("image_repository_id", "image", ["repository_id"], unique=False)
    op.create_index(
        "image_repository_id_docker_image_id",
        "image",
        ["repository_id", "docker_image_id"],
        unique=True,
    )
    op.create_index("image_security_indexed", "image", ["security_indexed"], unique=False)
    op.create_index(
        "image_security_indexed_engine", "image", ["security_indexed_engine"], unique=False
    )
    op.create_index(
        "image_security_indexed_engine_security_indexed",
        "image",
        ["security_indexed_engine", "security_indexed"],
        unique=False,
    )
    op.create_index("image_storage_id", "image", ["storage_id"], unique=False)
    op.create_table(
        "oauthaccesstoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("authorized_user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.String(length=255), nullable=False),
        sa.Column("token_type", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("refresh_token", sa.String(length=255), nullable=True),
        sa.Column("data", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["oauthapplication.id"],
            name=op.f("fk_oauthaccesstoken_application_id_oauthapplication"),
        ),
        sa.ForeignKeyConstraint(
            ["authorized_user_id"],
            ["user.id"],
            name=op.f("fk_oauthaccesstoken_authorized_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauthaccesstoken")),
    )
    op.create_index(
        "oauthaccesstoken_access_token", "oauthaccesstoken", ["access_token"], unique=False
    )
    op.create_index(
        "oauthaccesstoken_application_id", "oauthaccesstoken", ["application_id"], unique=False
    )
    op.create_index(
        "oauthaccesstoken_authorized_user_id",
        "oauthaccesstoken",
        ["authorized_user_id"],
        unique=False,
    )
    op.create_index(
        "oauthaccesstoken_refresh_token", "oauthaccesstoken", ["refresh_token"], unique=False
    )
    op.create_index("oauthaccesstoken_uuid", "oauthaccesstoken", ["uuid"], unique=False)
    op.create_table(
        "oauthauthorizationcode",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["oauthapplication.id"],
            name=op.f("fk_oauthauthorizationcode_application_id_oauthapplication"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauthauthorizationcode")),
    )
    op.create_index(
        "oauthauthorizationcode_application_id",
        "oauthauthorizationcode",
        ["application_id"],
        unique=False,
    )
    op.create_index("oauthauthorizationcode_code", "oauthauthorizationcode", ["code"], unique=False)
    op.create_table(
        "permissionprototype",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("activating_user_id", sa.Integer(), nullable=True),
        sa.Column("delegate_user_id", sa.Integer(), nullable=True),
        sa.Column("delegate_team_id", sa.Integer(), nullable=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["activating_user_id"],
            ["user.id"],
            name=op.f("fk_permissionprototype_activating_user_id_user"),
        ),
        sa.ForeignKeyConstraint(
            ["delegate_team_id"],
            ["team.id"],
            name=op.f("fk_permissionprototype_delegate_team_id_team"),
        ),
        sa.ForeignKeyConstraint(
            ["delegate_user_id"],
            ["user.id"],
            name=op.f("fk_permissionprototype_delegate_user_id_user"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["user.id"], name=op.f("fk_permissionprototype_org_id_user")
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name=op.f("fk_permissionprototype_role_id_role")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissionprototype")),
    )
    op.create_index(
        "permissionprototype_activating_user_id",
        "permissionprototype",
        ["activating_user_id"],
        unique=False,
    )
    op.create_index(
        "permissionprototype_delegate_team_id",
        "permissionprototype",
        ["delegate_team_id"],
        unique=False,
    )
    op.create_index(
        "permissionprototype_delegate_user_id",
        "permissionprototype",
        ["delegate_user_id"],
        unique=False,
    )
    op.create_index("permissionprototype_org_id", "permissionprototype", ["org_id"], unique=False)
    op.create_index(
        "permissionprototype_org_id_activating_user_id",
        "permissionprototype",
        ["org_id", "activating_user_id"],
        unique=False,
    )
    op.create_index("permissionprototype_role_id", "permissionprototype", ["role_id"], unique=False)
    op.create_table(
        "repositoryactioncount",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositoryactioncount_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositoryactioncount")),
    )
    op.create_index("repositoryactioncount_date", "repositoryactioncount", ["date"], unique=False)
    op.create_index(
        "repositoryactioncount_repository_id",
        "repositoryactioncount",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "repositoryactioncount_repository_id_date",
        "repositoryactioncount",
        ["repository_id", "date"],
        unique=True,
    )
    op.create_table(
        "repositoryauthorizedemail",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositoryauthorizedemail_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositoryauthorizedemail")),
    )
    op.create_index(
        "repositoryauthorizedemail_code", "repositoryauthorizedemail", ["code"], unique=True
    )
    op.create_index(
        "repositoryauthorizedemail_email_repository_id",
        "repositoryauthorizedemail",
        ["email", "repository_id"],
        unique=True,
    )
    op.create_index(
        "repositoryauthorizedemail_repository_id",
        "repositoryauthorizedemail",
        ["repository_id"],
        unique=False,
    )
    op.create_table(
        "repositorynotification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("method_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("event_config_json", UTF8LongText(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["externalnotificationevent.id"],
            name=op.f("fk_repositorynotification_event_id_externalnotificationevent"),
        ),
        sa.ForeignKeyConstraint(
            ["method_id"],
            ["externalnotificationmethod.id"],
            name=op.f("fk_repositorynotification_method_id_externalnotificationmethod"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorynotification_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorynotification")),
    )
    op.create_index(
        "repositorynotification_event_id", "repositorynotification", ["event_id"], unique=False
    )
    op.create_index(
        "repositorynotification_method_id", "repositorynotification", ["method_id"], unique=False
    )
    op.create_index(
        "repositorynotification_repository_id",
        "repositorynotification",
        ["repository_id"],
        unique=False,
    )
    op.create_index("repositorynotification_uuid", "repositorynotification", ["uuid"], unique=False)
    op.create_table(
        "repositorypermission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorypermission_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name=op.f("fk_repositorypermission_role_id_role")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["team.id"], name=op.f("fk_repositorypermission_team_id_team")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_repositorypermission_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorypermission")),
    )
    op.create_index(
        "repositorypermission_repository_id",
        "repositorypermission",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "repositorypermission_role_id", "repositorypermission", ["role_id"], unique=False
    )
    op.create_index(
        "repositorypermission_team_id", "repositorypermission", ["team_id"], unique=False
    )
    op.create_index(
        "repositorypermission_team_id_repository_id",
        "repositorypermission",
        ["team_id", "repository_id"],
        unique=True,
    )
    op.create_index(
        "repositorypermission_user_id", "repositorypermission", ["user_id"], unique=False
    )
    op.create_index(
        "repositorypermission_user_id_repository_id",
        "repositorypermission",
        ["user_id", "repository_id"],
        unique=True,
    )
    op.create_table(
        "star",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repository.id"], name=op.f("fk_star_repository_id_repository")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_star_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_star")),
    )
    op.create_index("star_repository_id", "star", ["repository_id"], unique=False)
    op.create_index("star_user_id", "star", ["user_id"], unique=False)
    op.create_index("star_user_id_repository_id", "star", ["user_id", "repository_id"], unique=True)
    op.create_table(
        "teammember",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], name=op.f("fk_teammember_team_id_team")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_teammember_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teammember")),
    )
    op.create_index("teammember_team_id", "teammember", ["team_id"], unique=False)
    op.create_index("teammember_user_id", "teammember", ["user_id"], unique=False)
    op.create_index("teammember_user_id_team_id", "teammember", ["user_id", "team_id"], unique=True)
    op.create_table(
        "teammemberinvite",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("inviter_id", sa.Integer(), nullable=False),
        sa.Column("invite_token", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["inviter_id"], ["user.id"], name=op.f("fk_teammemberinvite_inviter_id_user")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["team.id"], name=op.f("fk_teammemberinvite_team_id_team")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name=op.f("fk_teammemberinvite_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teammemberinvite")),
    )
    op.create_index("teammemberinvite_inviter_id", "teammemberinvite", ["inviter_id"], unique=False)
    op.create_index("teammemberinvite_team_id", "teammemberinvite", ["team_id"], unique=False)
    op.create_index("teammemberinvite_user_id", "teammemberinvite", ["user_id"], unique=False)
    op.create_table(
        "derivedstorageforimage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_image_id", sa.Integer(), nullable=False),
        sa.Column("derivative_id", sa.Integer(), nullable=False),
        sa.Column("transformation_id", sa.Integer(), nullable=False),
        sa.Column("uniqueness_hash", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["derivative_id"],
            ["imagestorage.id"],
            name=op.f("fk_derivedstorageforimage_derivative_id_imagestorage"),
        ),
        sa.ForeignKeyConstraint(
            ["source_image_id"],
            ["image.id"],
            name=op.f("fk_derivedstorageforimage_source_image_id_image"),
        ),
        sa.ForeignKeyConstraint(
            ["transformation_id"],
            ["imagestoragetransformation.id"],
            name=op.f("fk_derivedstorageforimage_transformation_constraint"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_derivedstorageforimage")),
    )
    op.create_index(
        "derivedstorageforimage_derivative_id",
        "derivedstorageforimage",
        ["derivative_id"],
        unique=False,
    )
    op.create_index(
        "derivedstorageforimage_source_image_id",
        "derivedstorageforimage",
        ["source_image_id"],
        unique=False,
    )
    op.create_index(
        "uniqueness_index",
        "derivedstorageforimage",
        ["source_image_id", "transformation_id", "uniqueness_hash"],
        unique=True,
    )
    op.create_index(
        "derivedstorageforimage_transformation_id",
        "derivedstorageforimage",
        ["transformation_id"],
        unique=False,
    )
    op.create_table(
        "repositorybuildtrigger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("connected_user_id", sa.Integer(), nullable=False),
        sa.Column("auth_token", sa.String(length=255), nullable=True),
        sa.Column("private_key", sa.Text(), nullable=True),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("write_token_id", sa.Integer(), nullable=True),
        sa.Column("pull_robot_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["connected_user_id"],
            ["user.id"],
            name=op.f("fk_repositorybuildtrigger_connected_user_id_user"),
        ),
        sa.ForeignKeyConstraint(
            ["pull_robot_id"],
            ["user.id"],
            name=op.f("fk_repositorybuildtrigger_pull_robot_id_user"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorybuildtrigger_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["buildtriggerservice.id"],
            name=op.f("fk_repositorybuildtrigger_service_id_buildtriggerservice"),
        ),
        sa.ForeignKeyConstraint(
            ["write_token_id"],
            ["accesstoken.id"],
            name=op.f("fk_repositorybuildtrigger_write_token_id_accesstoken"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorybuildtrigger")),
    )
    op.create_index(
        "repositorybuildtrigger_connected_user_id",
        "repositorybuildtrigger",
        ["connected_user_id"],
        unique=False,
    )
    op.create_index(
        "repositorybuildtrigger_pull_robot_id",
        "repositorybuildtrigger",
        ["pull_robot_id"],
        unique=False,
    )
    op.create_index(
        "repositorybuildtrigger_repository_id",
        "repositorybuildtrigger",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "repositorybuildtrigger_service_id", "repositorybuildtrigger", ["service_id"], unique=False
    )
    op.create_index(
        "repositorybuildtrigger_write_token_id",
        "repositorybuildtrigger",
        ["write_token_id"],
        unique=False,
    )
    op.create_table(
        "repositorytag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("lifetime_start_ts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lifetime_end_ts", sa.Integer(), nullable=True),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
        sa.Column(
            "reversion", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["image.id"], name=op.f("fk_repositorytag_image_id_image")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorytag_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorytag")),
    )
    op.create_index("repositorytag_image_id", "repositorytag", ["image_id"], unique=False)
    op.create_index(
        "repositorytag_lifetime_end_ts", "repositorytag", ["lifetime_end_ts"], unique=False
    )
    op.create_index("repositorytag_repository_id", "repositorytag", ["repository_id"], unique=False)
    op.create_index(
        "repositorytag_repository_id_name", "repositorytag", ["repository_id", "name"], unique=False
    )
    op.create_index(
        "repositorytag_repository_id_name_lifetime_end_ts",
        "repositorytag",
        ["repository_id", "name", "lifetime_end_ts"],
        unique=True,
    )
    op.create_table(
        "repositorybuild",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("access_token_id", sa.Integer(), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=True),
        sa.Column("job_config", sa.Text(), nullable=False),
        sa.Column("phase", sa.String(length=255), nullable=False),
        sa.Column("started", sa.DateTime(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("trigger_id", sa.Integer(), nullable=True),
        sa.Column("pull_robot_id", sa.Integer(), nullable=True),
        sa.Column(
            "logs_archived", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.Column("queue_id", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["access_token_id"],
            ["accesstoken.id"],
            name=op.f("fk_repositorybuild_access_token_id_accesstoken"),
        ),
        sa.ForeignKeyConstraint(
            ["pull_robot_id"], ["user.id"], name=op.f("fk_repositorybuild_pull_robot_id_user")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorybuild_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["trigger_id"],
            ["repositorybuildtrigger.id"],
            name=op.f("fk_repositorybuild_trigger_id_repositorybuildtrigger"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorybuild")),
    )
    op.create_index(
        "repositorybuild_access_token_id", "repositorybuild", ["access_token_id"], unique=False
    )
    op.create_index(
        "repositorybuild_pull_robot_id", "repositorybuild", ["pull_robot_id"], unique=False
    )
    op.create_index("repositorybuild_queue_id", "repositorybuild", ["queue_id"], unique=False)
    op.create_index(
        "repositorybuild_repository_id", "repositorybuild", ["repository_id"], unique=False
    )
    op.create_index(
        "repositorybuild_repository_id_started_phase",
        "repositorybuild",
        ["repository_id", "started", "phase"],
        unique=False,
    )
    op.create_index(
        "repositorybuild_resource_key", "repositorybuild", ["resource_key"], unique=False
    )
    op.create_index("repositorybuild_started", "repositorybuild", ["started"], unique=False)
    op.create_index(
        "repositorybuild_started_logs_archived_phase",
        "repositorybuild",
        ["started", "logs_archived", "phase"],
        unique=False,
    )
    op.create_index("repositorybuild_trigger_id", "repositorybuild", ["trigger_id"], unique=False)
    op.create_index("repositorybuild_uuid", "repositorybuild", ["uuid"], unique=False)
    op.create_table(
        "tagmanifest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=255), nullable=False),
        sa.Column("json_data", UTF8LongText(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["repositorytag.id"], name=op.f("fk_tagmanifest_tag_id_repositorytag")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagmanifest")),
    )
    op.create_index("tagmanifest_digest", "tagmanifest", ["digest"], unique=False)
    op.create_index("tagmanifest_tag_id", "tagmanifest", ["tag_id"], unique=True)
    op.create_table(
        "tagmanifestlabel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("annotated_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["annotated_id"],
            ["tagmanifest.id"],
            name=op.f("fk_tagmanifestlabel_annotated_id_tagmanifest"),
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["label.id"], name=op.f("fk_tagmanifestlabel_label_id_label")
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_tagmanifestlabel_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tagmanifestlabel")),
    )
    op.create_index(
        "tagmanifestlabel_annotated_id", "tagmanifestlabel", ["annotated_id"], unique=False
    )
    op.create_index(
        "tagmanifestlabel_annotated_id_label_id",
        "tagmanifestlabel",
        ["annotated_id", "label_id"],
        unique=True,
    )
    op.create_index("tagmanifestlabel_label_id", "tagmanifestlabel", ["label_id"], unique=False)
    op.create_index(
        "tagmanifestlabel_repository_id", "tagmanifestlabel", ["repository_id"], unique=False
    )

    op.bulk_insert(
        tables.accesstokenkind,
        [
            {"name": "build-worker"},
            {"name": "pushpull-token"},
        ],
    )

    op.bulk_insert(
        tables.buildtriggerservice,
        [
            {"name": "github"},
            {"name": "gitlab"},
            {"name": "bitbucket"},
            {"name": "custom-git"},
        ],
    )

    op.bulk_insert(
        tables.externalnotificationevent,
        [
            {"name": "build_failure"},
            {"name": "build_queued"},
            {"name": "build_start"},
            {"name": "build_success"},
            {"name": "repo_push"},
            {"name": "vulnerability_found"},
        ],
    )

    op.bulk_insert(
        tables.externalnotificationmethod,
        [
            {"name": "email"},
            {"name": "flowdock"},
            {"name": "hipchat"},
            {"name": "quay_notification"},
            {"name": "slack"},
            {"name": "webhook"},
        ],
    )

    op.bulk_insert(
        tables.imagestoragelocation,
        [
            {"name": "s3_us_east_1"},
            {"name": "s3_eu_west_1"},
            {"name": "s3_ap_southeast_1"},
            {"name": "s3_ap_southeast_2"},
            {"name": "s3_ap_northeast_1"},
            {"name": "s3_sa_east_1"},
            {"name": "local"},
            {"name": "s3_us_west_1"},
        ],
    )

    op.bulk_insert(
        tables.imagestoragesignaturekind,
        [
            {"name": "gpg2"},
        ],
    )

    op.bulk_insert(
        tables.imagestoragetransformation,
        [
            {"name": "squash"},
            {"name": "aci"},
        ],
    )

    op.bulk_insert(
        tables.labelsourcetype,
        [
            {"name": "manifest", "mutable": False},
            {"name": "api", "mutable": True},
            {"name": "internal", "mutable": False},
        ],
    )

    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "account_change_cc"},
            {"name": "account_change_password"},
            {"name": "account_change_plan"},
            {"name": "account_convert"},
            {"name": "add_repo_accesstoken"},
            {"name": "add_repo_notification"},
            {"name": "add_repo_permission"},
            {"name": "add_repo_webhook"},
            {"name": "build_dockerfile"},
            {"name": "change_repo_permission"},
            {"name": "change_repo_visibility"},
            {"name": "create_application"},
            {"name": "create_prototype_permission"},
            {"name": "create_repo"},
            {"name": "create_robot"},
            {"name": "create_tag"},
            {"name": "delete_application"},
            {"name": "delete_prototype_permission"},
            {"name": "delete_repo"},
            {"name": "delete_repo_accesstoken"},
            {"name": "delete_repo_notification"},
            {"name": "delete_repo_permission"},
            {"name": "delete_repo_trigger"},
            {"name": "delete_repo_webhook"},
            {"name": "delete_robot"},
            {"name": "delete_tag"},
            {"name": "manifest_label_add"},
            {"name": "manifest_label_delete"},
            {"name": "modify_prototype_permission"},
            {"name": "move_tag"},
            {"name": "org_add_team_member"},
            {"name": "org_create_team"},
            {"name": "org_delete_team"},
            {"name": "org_delete_team_member_invite"},
            {"name": "org_invite_team_member"},
            {"name": "org_remove_team_member"},
            {"name": "org_set_team_description"},
            {"name": "org_set_team_role"},
            {"name": "org_team_member_invite_accepted"},
            {"name": "org_team_member_invite_declined"},
            {"name": "pull_repo"},
            {"name": "push_repo"},
            {"name": "regenerate_robot_token"},
            {"name": "repo_verb"},
            {"name": "reset_application_client_secret"},
            {"name": "revert_tag"},
            {"name": "service_key_approve"},
            {"name": "service_key_create"},
            {"name": "service_key_delete"},
            {"name": "service_key_extend"},
            {"name": "service_key_modify"},
            {"name": "service_key_rotate"},
            {"name": "setup_repo_trigger"},
            {"name": "set_repo_description"},
            {"name": "take_ownership"},
            {"name": "update_application"},
        ],
    )

    op.bulk_insert(
        tables.loginservice,
        [
            {"name": "github"},
            {"name": "quayrobot"},
            {"name": "ldap"},
            {"name": "google"},
            {"name": "keystone"},
            {"name": "dex"},
            {"name": "jwtauthn"},
        ],
    )

    op.bulk_insert(
        tables.mediatype,
        [
            {"name": "text/plain"},
            {"name": "application/json"},
        ],
    )

    op.bulk_insert(
        tables.notificationkind,
        [
            {"name": "build_failure"},
            {"name": "build_queued"},
            {"name": "build_start"},
            {"name": "build_success"},
            {"name": "expiring_license"},
            {"name": "maintenance"},
            {"name": "org_team_invite"},
            {"name": "over_private_usage"},
            {"name": "password_required"},
            {"name": "repo_push"},
            {"name": "service_key_submitted"},
            {"name": "vulnerability_found"},
        ],
    )

    op.bulk_insert(
        tables.role,
        [
            {"name": "admin"},
            {"name": "write"},
            {"name": "read"},
        ],
    )

    op.bulk_insert(
        tables.teamrole,
        [
            {"name": "admin"},
            {"name": "creator"},
            {"name": "member"},
        ],
    )

    op.bulk_insert(
        tables.visibility,
        [
            {"name": "public"},
            {"name": "private"},
        ],
    )

    # ### population of test data ### #
    tester.populate_table(
        "user",
        [
            ("uuid", tester.TestDataType.UUID),
            ("username", tester.TestDataType.String),
            ("password_hash", tester.TestDataType.String),
            ("email", tester.TestDataType.String),
            ("verified", tester.TestDataType.Boolean),
            ("organization", tester.TestDataType.Boolean),
            ("robot", tester.TestDataType.Boolean),
            ("invoice_email", tester.TestDataType.Boolean),
            ("invalid_login_attempts", tester.TestDataType.Integer),
            ("last_invalid_login", tester.TestDataType.DateTime),
            ("removed_tag_expiration_s", tester.TestDataType.Integer),
            ("enabled", tester.TestDataType.Boolean),
            ("invoice_email_address", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "repository",
        [
            ("namespace_user_id", tester.TestDataType.Foreign("user")),
            ("name", tester.TestDataType.String),
            ("visibility_id", tester.TestDataType.Foreign("visibility")),
            ("description", tester.TestDataType.String),
            ("badge_token", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "emailconfirmation",
        [
            ("code", tester.TestDataType.String),
            ("user_id", tester.TestDataType.Foreign("user")),
            ("pw_reset", tester.TestDataType.Boolean),
            ("email_confirm", tester.TestDataType.Boolean),
            ("created", tester.TestDataType.DateTime),
        ],
    )

    tester.populate_table(
        "federatedlogin",
        [
            ("user_id", tester.TestDataType.Foreign("user")),
            ("service_id", tester.TestDataType.Foreign("loginservice")),
            ("service_ident", tester.TestDataType.String),
            ("metadata_json", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "imagestorage",
        [
            ("uuid", tester.TestDataType.UUID),
            ("checksum", tester.TestDataType.String),
            ("image_size", tester.TestDataType.BigInteger),
            ("uncompressed_size", tester.TestDataType.BigInteger),
            ("uploading", tester.TestDataType.Boolean),
            ("cas_path", tester.TestDataType.Boolean),
            ("content_checksum", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "image",
        [
            ("docker_image_id", tester.TestDataType.UUID),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("ancestors", tester.TestDataType.String),
            ("storage_id", tester.TestDataType.Foreign("imagestorage")),
            ("security_indexed", tester.TestDataType.Boolean),
            ("security_indexed_engine", tester.TestDataType.Integer),
        ],
    )

    tester.populate_table(
        "imagestorageplacement",
        [
            ("storage_id", tester.TestDataType.Foreign("imagestorage")),
            ("location_id", tester.TestDataType.Foreign("imagestoragelocation")),
        ],
    )

    tester.populate_table(
        "messages",
        [
            ("content", tester.TestDataType.String),
            ("uuid", tester.TestDataType.UUID),
        ],
    )

    tester.populate_table(
        "queueitem",
        [
            ("queue_name", tester.TestDataType.String),
            ("body", tester.TestDataType.JSON),
            ("available_after", tester.TestDataType.DateTime),
            ("available", tester.TestDataType.Boolean),
            ("processing_expires", tester.TestDataType.DateTime),
            ("retries_remaining", tester.TestDataType.Integer),
        ],
    )

    tester.populate_table(
        "servicekeyapproval",
        [
            ("approver_id", tester.TestDataType.Foreign("user")),
            ("approval_type", tester.TestDataType.String),
            ("approved_date", tester.TestDataType.DateTime),
            ("notes", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "servicekey",
        [
            ("name", tester.TestDataType.String),
            ("kid", tester.TestDataType.String),
            ("service", tester.TestDataType.String),
            ("jwk", tester.TestDataType.JSON),
            ("metadata", tester.TestDataType.JSON),
            ("created_date", tester.TestDataType.DateTime),
            ("approval_id", tester.TestDataType.Foreign("servicekeyapproval")),
        ],
    )

    tester.populate_table(
        "label",
        [
            ("uuid", tester.TestDataType.UUID),
            ("key", tester.TestDataType.UTF8Char),
            ("value", tester.TestDataType.JSON),
            ("media_type_id", tester.TestDataType.Foreign("mediatype")),
            ("source_type_id", tester.TestDataType.Foreign("labelsourcetype")),
        ],
    )

    tester.populate_table(
        "logentry",
        [
            ("kind_id", tester.TestDataType.Foreign("logentrykind")),
            ("account_id", tester.TestDataType.Foreign("user")),
            ("performer_id", tester.TestDataType.Foreign("user")),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("datetime", tester.TestDataType.DateTime),
            ("ip", tester.TestDataType.String),
            ("metadata_json", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "notification",
        [
            ("uuid", tester.TestDataType.UUID),
            ("kind_id", tester.TestDataType.Foreign("notificationkind")),
            ("target_id", tester.TestDataType.Foreign("user")),
            ("metadata_json", tester.TestDataType.JSON),
            ("created", tester.TestDataType.DateTime),
            ("dismissed", tester.TestDataType.Boolean),
            ("lookup_path", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "oauthapplication",
        [
            ("client_id", tester.TestDataType.String),
            ("client_secret", tester.TestDataType.String),
            ("redirect_uri", tester.TestDataType.String),
            ("application_uri", tester.TestDataType.String),
            ("organization_id", tester.TestDataType.Foreign("user")),
            ("name", tester.TestDataType.String),
            ("description", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "team",
        [
            ("name", tester.TestDataType.String),
            ("organization_id", tester.TestDataType.Foreign("user")),
            ("role_id", tester.TestDataType.Foreign("teamrole")),
            ("description", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "torrentinfo",
        [
            ("storage_id", tester.TestDataType.Foreign("imagestorage")),
            ("piece_length", tester.TestDataType.Integer),
            ("pieces", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "userregion",
        [
            ("user_id", tester.TestDataType.Foreign("user")),
            ("location_id", tester.TestDataType.Foreign("imagestoragelocation")),
        ],
    )

    tester.populate_table(
        "accesstoken",
        [
            ("friendly_name", tester.TestDataType.String),
            ("code", tester.TestDataType.Token),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("created", tester.TestDataType.DateTime),
            ("role_id", tester.TestDataType.Foreign("role")),
            ("temporary", tester.TestDataType.Boolean),
            ("kind_id", tester.TestDataType.Foreign("accesstokenkind")),
        ],
    )

    tester.populate_table(
        "blobupload",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("uuid", tester.TestDataType.UUID),
            ("byte_count", tester.TestDataType.Integer),
            ("sha_state", tester.TestDataType.String),
            ("location_id", tester.TestDataType.Foreign("imagestoragelocation")),
            ("chunk_count", tester.TestDataType.Integer),
            ("created", tester.TestDataType.DateTime),
        ],
    )

    tester.populate_table(
        "oauthaccesstoken",
        [
            ("uuid", tester.TestDataType.UUID),
            ("application_id", tester.TestDataType.Foreign("oauthapplication")),
            ("authorized_user_id", tester.TestDataType.Foreign("user")),
            ("scope", tester.TestDataType.String),
            ("access_token", tester.TestDataType.Token),
            ("token_type", tester.TestDataType.String),
            ("expires_at", tester.TestDataType.DateTime),
            ("data", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "oauthauthorizationcode",
        [
            ("application_id", tester.TestDataType.Foreign("oauthapplication")),
            ("code", tester.TestDataType.Token),
            ("scope", tester.TestDataType.String),
            ("data", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "permissionprototype",
        [
            ("org_id", tester.TestDataType.Foreign("user")),
            ("uuid", tester.TestDataType.UUID),
            ("activating_user_id", tester.TestDataType.Foreign("user")),
            ("delegate_user_id", tester.TestDataType.Foreign("user")),
            ("role_id", tester.TestDataType.Foreign("role")),
        ],
    )

    tester.populate_table(
        "repositoryactioncount",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("count", tester.TestDataType.Integer),
            ("date", tester.TestDataType.Date),
        ],
    )

    tester.populate_table(
        "repositoryauthorizedemail",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("email", tester.TestDataType.String),
            ("code", tester.TestDataType.String),
            ("confirmed", tester.TestDataType.Boolean),
        ],
    )

    tester.populate_table(
        "repositorynotification",
        [
            ("uuid", tester.TestDataType.UUID),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("event_id", tester.TestDataType.Foreign("externalnotificationevent")),
            ("method_id", tester.TestDataType.Foreign("externalnotificationmethod")),
            ("title", tester.TestDataType.String),
            ("config_json", tester.TestDataType.JSON),
            ("event_config_json", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "repositorypermission",
        [
            ("team_id", tester.TestDataType.Foreign("team")),
            ("user_id", tester.TestDataType.Foreign("user")),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("role_id", tester.TestDataType.Foreign("role")),
        ],
    )

    tester.populate_table(
        "star",
        [
            ("user_id", tester.TestDataType.Foreign("user")),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("created", tester.TestDataType.DateTime),
        ],
    )

    tester.populate_table(
        "teammember",
        [
            ("user_id", tester.TestDataType.Foreign("user")),
            ("team_id", tester.TestDataType.Foreign("team")),
        ],
    )

    tester.populate_table(
        "teammemberinvite",
        [
            ("user_id", tester.TestDataType.Foreign("user")),
            ("email", tester.TestDataType.String),
            ("team_id", tester.TestDataType.Foreign("team")),
            ("inviter_id", tester.TestDataType.Foreign("user")),
            ("invite_token", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "derivedstorageforimage",
        [
            ("source_image_id", tester.TestDataType.Foreign("image")),
            ("derivative_id", tester.TestDataType.Foreign("imagestorage")),
            ("transformation_id", tester.TestDataType.Foreign("imagestoragetransformation")),
            ("uniqueness_hash", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "repositorybuildtrigger",
        [
            ("uuid", tester.TestDataType.UUID),
            ("service_id", tester.TestDataType.Foreign("buildtriggerservice")),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("connected_user_id", tester.TestDataType.Foreign("user")),
            ("auth_token", tester.TestDataType.String),
            ("config", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "repositorytag",
        [
            ("name", tester.TestDataType.String),
            ("image_id", tester.TestDataType.Foreign("image")),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("lifetime_start_ts", tester.TestDataType.Integer),
            ("hidden", tester.TestDataType.Boolean),
            ("reversion", tester.TestDataType.Boolean),
        ],
    )

    tester.populate_table(
        "repositorybuild",
        [
            ("uuid", tester.TestDataType.UUID),
            ("phase", tester.TestDataType.String),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("access_token_id", tester.TestDataType.Foreign("accesstoken")),
            ("resource_key", tester.TestDataType.String),
            ("job_config", tester.TestDataType.JSON),
            ("started", tester.TestDataType.DateTime),
            ("display_name", tester.TestDataType.JSON),
            ("trigger_id", tester.TestDataType.Foreign("repositorybuildtrigger")),
            ("logs_archived", tester.TestDataType.Boolean),
        ],
    )

    tester.populate_table(
        "tagmanifest",
        [
            ("tag_id", tester.TestDataType.Foreign("repositorytag")),
            ("digest", tester.TestDataType.String),
            ("json_data", tester.TestDataType.JSON),
        ],
    )

    tester.populate_table(
        "tagmanifestlabel",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("annotated_id", tester.TestDataType.Foreign("tagmanifest")),
            ("label_id", tester.TestDataType.Foreign("label")),
        ],
    )
    # ### end population of test data ### #


def downgrade(op, tables, tester):
    op.drop_table("tagmanifestlabel")
    op.drop_table("tagmanifest")
    op.drop_table("repositorybuild")
    op.drop_table("repositorytag")
    op.drop_table("repositorybuildtrigger")
    op.drop_table("derivedstorageforimage")
    op.drop_table("teammemberinvite")
    op.drop_table("teammember")
    op.drop_table("star")
    op.drop_table("repositorypermission")
    op.drop_table("repositorynotification")
    op.drop_table("repositoryauthorizedemail")
    op.drop_table("repositoryactioncount")
    op.drop_table("permissionprototype")
    op.drop_table("oauthauthorizationcode")
    op.drop_table("oauthaccesstoken")
    op.drop_table("image")
    op.drop_table("blobupload")
    op.drop_table("accesstoken")
    op.drop_table("userregion")
    op.drop_table("torrentinfo")
    op.drop_table("team")
    op.drop_table("servicekey")
    op.drop_table("repository")
    op.drop_table("quayrelease")
    op.drop_table("oauthapplication")
    op.drop_table("notification")
    op.drop_table("logentry")
    op.drop_table("label")
    op.drop_table("imagestoragesignature")
    op.drop_table("imagestorageplacement")
    op.drop_table("federatedlogin")
    op.drop_table("emailconfirmation")
    op.drop_table("visibility")
    op.drop_table("user")
    op.drop_table("teamrole")
    op.drop_table("servicekeyapproval")
    op.drop_table("role")
    op.drop_table("queueitem")
    op.drop_table("quayservice")
    op.drop_table("quayregion")
    op.drop_table("notificationkind")
    op.drop_table("messages")
    op.drop_table("mediatype")
    op.drop_table("loginservice")
    op.drop_table("logentrykind")
    op.drop_table("labelsourcetype")
    op.drop_table("imagestoragetransformation")
    op.drop_table("imagestoragesignaturekind")
    op.drop_table("imagestoragelocation")
    op.drop_table("imagestorage")
    op.drop_table("externalnotificationmethod")
    op.drop_table("externalnotificationevent")
    op.drop_table("buildtriggerservice")
    op.drop_table("accesstokenkind")
