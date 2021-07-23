import logging
import json
import hashlib
import random
import calendar
import os
import argparse

from datetime import datetime, timedelta, date
from freezegun import freeze_time
from peewee import SqliteDatabase
from itertools import count
from uuid import UUID, uuid4
from threading import Event

from app import app, storage as store, tf, docker_v2_signing_key
from email.utils import formatdate
from data.database import (
    db,
    db_encrypter,
    all_models,
    Role,
    TeamRole,
    Visibility,
    LoginService,
    BuildTriggerService,
    AccessTokenKind,
    LogEntryKind,
    ImageStorageLocation,
    ImageStorageTransformation,
    ImageStorageSignatureKind,
    ExternalNotificationEvent,
    ExternalNotificationMethod,
    NotificationKind,
    QuayRegion,
    QuayService,
    UserRegion,
    OAuthAuthorizationCode,
    ServiceKeyApprovalType,
    MediaType,
    LabelSourceType,
    UserPromptKind,
    RepositoryKind,
    User,
    DisableReason,
    DeletedNamespace,
    DeletedRepository,
    appr_classes,
    ApprTagKind,
    ApprBlobPlacementLocation,
    Repository,
    TagKind,
    ManifestChild,
    TagToRepositoryTag,
    get_epoch_timestamp_ms,
    RepoMirrorConfig,
    RepoMirrorRule,
    RepositoryState,
)
from data import model
from data.decorators import is_deprecated_model
from data.encryption import FieldEncrypter
from data.fields import Credential
from data.logs_model import logs_model
from data.queue import WorkQueue
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from digest.digest_tools import sha256_digest
from storage.basestorage import StoragePaths
from image.docker.schema1 import DOCKER_SCHEMA1_CONTENT_TYPES
from image.docker.schema2 import DOCKER_SCHEMA2_CONTENT_TYPES
from image.docker.schema1 import DockerSchema1ManifestBuilder
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from image.docker.schema2.config import DockerSchema2Config
from image.oci import OCI_CONTENT_TYPES


from workers import repositoryactioncounter


logger = logging.getLogger(__name__)


TEST_STRIPE_ID = "cus_2tmnh3PkXQS8NG"

IS_TESTING_REAL_DATABASE = bool(os.environ.get("TEST_DATABASE_URI"))

TEMP_BLOB_EXPIRATION = 120  # seconds


def __generate_service_key(
    kid,
    name,
    user,
    timestamp,
    approval_type,
    expiration=None,
    metadata=None,
    service="sample_service",
    rotation_duration=None,
):
    _, key = model.service_keys.generate_service_key(
        service,
        expiration,
        kid=kid,
        name=name,
        metadata=metadata,
        rotation_duration=rotation_duration,
    )

    if approval_type is not None:
        model.service_keys.approve_service_key(
            key.kid, approval_type, notes="The **test** approval"
        )

        key_metadata = {
            "kid": kid,
            "preshared": True,
            "service": service,
            "name": name,
            "expiration_date": expiration,
            "auto_approved": True,
        }

        logs_model.log_action(
            "service_key_approve", None, performer=user, timestamp=timestamp, metadata=key_metadata
        )

        logs_model.log_action(
            "service_key_create", None, performer=user, timestamp=timestamp, metadata=key_metadata
        )


def _populate_blob(repo, content):
    assert isinstance(repo, Repository)
    assert isinstance(content, bytes)
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = model.blob.store_blob_record_and_temp_link_in_repo(
        repo, digest, location, len(content), TEMP_BLOB_EXPIRATION
    )
    return blob, digest


def __create_manifest_and_tags(
    repo, structure, creator_username, tag_map, current_level=0, builder=None, last_leaf_id=None
):
    num_layers, subtrees, tag_names = structure

    num_layers = num_layers or 1

    tag_names = tag_names or []
    tag_names = [tag_names] if not isinstance(tag_names, list) else tag_names

    repo_ref = RepositoryReference.for_repo_obj(repo)
    builder = (
        builder
        if builder
        else DockerSchema1ManifestBuilder(repo.namespace_user.username, repo.name, "")
    )

    # TODO: Change this to a mixture of Schema1 and Schema2 manifest once we no longer need to
    # read from storage for Schema2.

    # Populate layers. Note, we do this in reverse order using insert_layer, as it is easier to
    # add the leaf last (even though Schema1 has it listed first).
    parent_id = last_leaf_id
    leaf_id = None
    for layer_index in range(0, num_layers):
        content = "layer-%s-%s-%s" % (layer_index, current_level, get_epoch_timestamp_ms())
        _, digest = _populate_blob(repo, content.encode("ascii"))
        current_id = "abcdef%s%s%s" % (layer_index, current_level, get_epoch_timestamp_ms())

        if layer_index == num_layers - 1:
            leaf_id = current_id

        config = {
            "id": current_id,
            "Size": len(content),
        }
        if parent_id:
            config["parent"] = parent_id

        builder.insert_layer(digest, json.dumps(config))
        parent_id = current_id

    for tag_name in tag_names:
        adjusted_tag_name = tag_name
        now = datetime.utcnow()
        if tag_name[0] == "#":
            adjusted_tag_name = tag_name[1:]
            now = now - timedelta(seconds=1)

        manifest = builder.clone(adjusted_tag_name).build()

        with freeze_time(now):
            created_tag, _ = registry_model.create_manifest_and_retarget_tag(
                repo_ref, manifest, adjusted_tag_name, store, raise_on_error=True
            )
            assert created_tag
            tag_map[adjusted_tag_name] = created_tag

    for subtree in subtrees:
        __create_manifest_and_tags(
            repo,
            subtree,
            creator_username,
            tag_map,
            current_level=current_level + 1,
            builder=builder,
            last_leaf_id=leaf_id,
        )


def __generate_repository(user_obj, name, description, is_public, permissions, structure):
    repo = model.repository.create_repository(user_obj.username, name, user_obj)

    if is_public:
        model.repository.set_repository_visibility(repo, "public")

    if description:
        repo.description = description
        repo.save()

    for delegate, role in permissions:
        model.permission.set_user_repo_permission(delegate.username, user_obj.username, name, role)

    tag_map = {}
    if isinstance(structure, list):
        for leaf in structure:
            __create_manifest_and_tags(repo, leaf, user_obj.username, tag_map)
    else:
        __create_manifest_and_tags(repo, structure, user_obj.username, tag_map)

    return repo


db_initialized_for_testing = Event()
testcases = {}


def finished_database_for_testing(testcase):
    """
    Called when a testcase has finished using the database, indicating that any changes should be
    discarded.
    """
    testcases[testcase]["savepoint"].rollback()
    testcases[testcase]["savepoint"].__exit__(True, None, None)

    testcases[testcase]["transaction"].__exit__(True, None, None)


def setup_database_for_testing(testcase):
    """
    Called when a testcase has started using the database, indicating that the database should be
    setup (if not already) and a savepoint created.
    """

    # Sanity check to make sure we're not killing our prod db
    if not IS_TESTING_REAL_DATABASE and not isinstance(db.obj, SqliteDatabase):
        raise RuntimeError("Attempted to wipe production database!")

    if not db_initialized_for_testing.is_set():
        logger.debug("Setting up DB for testing.")

        # Setup the database.
        if os.environ.get("SKIP_DB_SCHEMA", "") != "true":
            wipe_database()
            initialize_database()

        populate_database()

        models_missing_data = find_models_missing_data()
        if models_missing_data:
            raise RuntimeError(
                "%s models are missing data: %s", len(models_missing_data), models_missing_data
            )

        # Enable foreign key constraints.
        if not IS_TESTING_REAL_DATABASE:
            db.obj.execute_sql("PRAGMA foreign_keys = ON;")

        db_initialized_for_testing.set()

    # Initialize caches.
    Repository.kind.get_id("image")

    # Create a savepoint for the testcase.
    testcases[testcase] = {}
    testcases[testcase]["transaction"] = db.transaction()
    testcases[testcase]["transaction"].__enter__()

    testcases[testcase]["savepoint"] = db.savepoint()
    testcases[testcase]["savepoint"].__enter__()


def initialize_database():
    db_encrypter.initialize(FieldEncrypter("anothercrazykey!"))
    db.create_tables(all_models)

    Role.create(name="admin")
    Role.create(name="write")
    Role.create(name="read")
    TeamRole.create(name="admin")
    TeamRole.create(name="creator")
    TeamRole.create(name="member")
    Visibility.create(name="public")
    Visibility.create(name="private")

    LoginService.create(name="google")
    LoginService.create(name="github")
    LoginService.create(name="quayrobot")
    LoginService.create(name="ldap")
    LoginService.create(name="jwtauthn")
    LoginService.create(name="keystone")
    LoginService.create(name="dex")
    LoginService.create(name="oidc")

    BuildTriggerService.create(name="github")
    BuildTriggerService.create(name="custom-git")
    BuildTriggerService.create(name="bitbucket")
    BuildTriggerService.create(name="gitlab")

    AccessTokenKind.create(name="build-worker")
    AccessTokenKind.create(name="pushpull-token")

    LogEntryKind.create(name="account_change_plan")
    LogEntryKind.create(name="account_change_cc")
    LogEntryKind.create(name="account_change_password")
    LogEntryKind.create(name="account_convert")

    LogEntryKind.create(name="create_robot")
    LogEntryKind.create(name="delete_robot")

    LogEntryKind.create(name="create_repo")
    LogEntryKind.create(name="push_repo")
    LogEntryKind.create(name="pull_repo")
    LogEntryKind.create(name="delete_repo")
    LogEntryKind.create(name="create_tag")
    LogEntryKind.create(name="move_tag")
    LogEntryKind.create(name="delete_tag")
    LogEntryKind.create(name="revert_tag")
    LogEntryKind.create(name="add_repo_permission")
    LogEntryKind.create(name="change_repo_permission")
    LogEntryKind.create(name="delete_repo_permission")
    LogEntryKind.create(name="change_repo_visibility")
    LogEntryKind.create(name="change_repo_trust")
    LogEntryKind.create(name="add_repo_accesstoken")
    LogEntryKind.create(name="delete_repo_accesstoken")
    LogEntryKind.create(name="set_repo_description")
    LogEntryKind.create(name="change_repo_state")

    LogEntryKind.create(name="build_dockerfile")

    LogEntryKind.create(name="org_create_team")
    LogEntryKind.create(name="org_delete_team")
    LogEntryKind.create(name="org_invite_team_member")
    LogEntryKind.create(name="org_delete_team_member_invite")
    LogEntryKind.create(name="org_add_team_member")
    LogEntryKind.create(name="org_team_member_invite_accepted")
    LogEntryKind.create(name="org_team_member_invite_declined")
    LogEntryKind.create(name="org_remove_team_member")
    LogEntryKind.create(name="org_set_team_description")
    LogEntryKind.create(name="org_set_team_role")

    LogEntryKind.create(name="create_prototype_permission")
    LogEntryKind.create(name="modify_prototype_permission")
    LogEntryKind.create(name="delete_prototype_permission")

    LogEntryKind.create(name="setup_repo_trigger")
    LogEntryKind.create(name="delete_repo_trigger")

    LogEntryKind.create(name="create_application")
    LogEntryKind.create(name="update_application")
    LogEntryKind.create(name="delete_application")
    LogEntryKind.create(name="reset_application_client_secret")

    # Note: These next two are deprecated.
    LogEntryKind.create(name="add_repo_webhook")
    LogEntryKind.create(name="delete_repo_webhook")

    LogEntryKind.create(name="add_repo_notification")
    LogEntryKind.create(name="delete_repo_notification")
    LogEntryKind.create(name="reset_repo_notification")

    LogEntryKind.create(name="regenerate_robot_token")

    LogEntryKind.create(name="repo_verb")

    LogEntryKind.create(name="repo_mirror_enabled")
    LogEntryKind.create(name="repo_mirror_disabled")
    LogEntryKind.create(name="repo_mirror_config_changed")
    LogEntryKind.create(name="repo_mirror_sync_started")
    LogEntryKind.create(name="repo_mirror_sync_failed")
    LogEntryKind.create(name="repo_mirror_sync_success")
    LogEntryKind.create(name="repo_mirror_sync_now_requested")
    LogEntryKind.create(name="repo_mirror_sync_tag_success")
    LogEntryKind.create(name="repo_mirror_sync_tag_failed")
    LogEntryKind.create(name="repo_mirror_sync_test_success")
    LogEntryKind.create(name="repo_mirror_sync_test_failed")
    LogEntryKind.create(name="repo_mirror_sync_test_started")

    LogEntryKind.create(name="service_key_create")
    LogEntryKind.create(name="service_key_approve")
    LogEntryKind.create(name="service_key_delete")
    LogEntryKind.create(name="service_key_modify")
    LogEntryKind.create(name="service_key_extend")
    LogEntryKind.create(name="service_key_rotate")

    LogEntryKind.create(name="take_ownership")

    LogEntryKind.create(name="manifest_label_add")
    LogEntryKind.create(name="manifest_label_delete")

    LogEntryKind.create(name="change_tag_expiration")
    LogEntryKind.create(name="toggle_repo_trigger")

    LogEntryKind.create(name="create_app_specific_token")
    LogEntryKind.create(name="revoke_app_specific_token")

    ImageStorageLocation.create(name="local_eu")
    ImageStorageLocation.create(name="local_us")

    ApprBlobPlacementLocation.create(name="local_eu")
    ApprBlobPlacementLocation.create(name="local_us")

    ImageStorageTransformation.create(name="squash")
    ImageStorageTransformation.create(name="aci")

    ImageStorageSignatureKind.create(name="gpg2")

    # NOTE: These MUST be copied over to NotificationKind, since every external
    # notification can also generate a Quay.io notification.
    ExternalNotificationEvent.create(name="repo_push")
    ExternalNotificationEvent.create(name="build_queued")
    ExternalNotificationEvent.create(name="build_start")
    ExternalNotificationEvent.create(name="build_success")
    ExternalNotificationEvent.create(name="build_cancelled")
    ExternalNotificationEvent.create(name="build_failure")
    ExternalNotificationEvent.create(name="vulnerability_found")

    ExternalNotificationEvent.create(name="repo_mirror_sync_started")
    ExternalNotificationEvent.create(name="repo_mirror_sync_success")
    ExternalNotificationEvent.create(name="repo_mirror_sync_failed")

    ExternalNotificationMethod.create(name="quay_notification")
    ExternalNotificationMethod.create(name="email")
    ExternalNotificationMethod.create(name="webhook")

    ExternalNotificationMethod.create(name="flowdock")
    ExternalNotificationMethod.create(name="hipchat")
    ExternalNotificationMethod.create(name="slack")

    NotificationKind.create(name="repo_push")
    NotificationKind.create(name="build_queued")
    NotificationKind.create(name="build_start")
    NotificationKind.create(name="build_success")
    NotificationKind.create(name="build_cancelled")
    NotificationKind.create(name="build_failure")
    NotificationKind.create(name="vulnerability_found")
    NotificationKind.create(name="service_key_submitted")

    NotificationKind.create(name="password_required")
    NotificationKind.create(name="over_private_usage")
    NotificationKind.create(name="expiring_license")
    NotificationKind.create(name="maintenance")
    NotificationKind.create(name="org_team_invite")

    NotificationKind.create(name="repo_mirror_sync_started")
    NotificationKind.create(name="repo_mirror_sync_success")
    NotificationKind.create(name="repo_mirror_sync_failed")

    NotificationKind.create(name="test_notification")

    QuayRegion.create(name="us")
    QuayService.create(name="quay")

    MediaType.create(name="text/plain")
    MediaType.create(name="application/json")
    MediaType.create(name="text/markdown")
    MediaType.create(name="application/vnd.cnr.blob.v0.tar+gzip")
    MediaType.create(name="application/vnd.cnr.package-manifest.helm.v0.json")
    MediaType.create(name="application/vnd.cnr.package-manifest.kpm.v0.json")
    MediaType.create(name="application/vnd.cnr.package-manifest.docker-compose.v0.json")
    MediaType.create(name="application/vnd.cnr.package.kpm.v0.tar+gzip")
    MediaType.create(name="application/vnd.cnr.package.helm.v0.tar+gzip")
    MediaType.create(name="application/vnd.cnr.package.docker-compose.v0.tar+gzip")
    MediaType.create(name="application/vnd.cnr.manifests.v0.json")
    MediaType.create(name="application/vnd.cnr.manifest.list.v0.json")

    for media_type in DOCKER_SCHEMA1_CONTENT_TYPES:
        MediaType.create(name=media_type)

    for media_type in DOCKER_SCHEMA2_CONTENT_TYPES:
        MediaType.create(name=media_type)

    for media_type in OCI_CONTENT_TYPES:
        MediaType.create(name=media_type)

    LabelSourceType.create(name="manifest")
    LabelSourceType.create(name="api", mutable=True)
    LabelSourceType.create(name="internal")

    UserPromptKind.create(name="confirm_username")
    UserPromptKind.create(name="enter_name")
    UserPromptKind.create(name="enter_company")

    RepositoryKind.create(name="image")
    RepositoryKind.create(name="application")

    ApprTagKind.create(name="tag")
    ApprTagKind.create(name="release")
    ApprTagKind.create(name="channel")

    DisableReason.create(name="user_toggled")
    DisableReason.create(name="successive_build_failures")
    DisableReason.create(name="successive_build_internal_errors")

    TagKind.create(name="tag")


def wipe_database():
    logger.debug("Wiping all data from the DB.")

    # Sanity check to make sure we're not killing our prod db
    if not IS_TESTING_REAL_DATABASE and not isinstance(db.obj, SqliteDatabase):
        raise RuntimeError("Attempted to wipe production database!")

    db.drop_tables(all_models)


def populate_database(minimal=False):
    logger.debug("Populating the DB with test data.")

    # Check if the data already exists. If so, we skip. This can happen between calls from the
    # "old style" tests and the new py.test's.
    try:
        User.get(username="devtable")
        logger.debug("DB already populated")
        return
    except User.DoesNotExist:
        pass

    # Note: databases set up with "real" schema (via Alembic) will not have these types
    # type, so we it here it necessary.
    try:
        ImageStorageLocation.get(name="local_eu")
        ImageStorageLocation.get(name="local_us")
    except ImageStorageLocation.DoesNotExist:
        ImageStorageLocation.create(name="local_eu")
        ImageStorageLocation.create(name="local_us")

    try:
        NotificationKind.get(name="test_notification")
    except NotificationKind.DoesNotExist:
        NotificationKind.create(name="test_notification")

    new_user_1 = model.user.create_user("devtable", "password", "jschorr@devtable.com")
    new_user_1.verified = True
    new_user_1.stripe_id = TEST_STRIPE_ID
    new_user_1.save()

    if minimal:
        logger.debug("Skipping most db population because user requested mininal db")
        return

    UserRegion.create(user=new_user_1, location=ImageStorageLocation.get(name="local_us"))
    model.release.set_region_release("quay", "us", "v0.1.2")

    model.user.create_confirm_email_code(new_user_1, new_email="typo@devtable.com")

    disabled_user = model.user.create_user("disabled", "password", "jschorr+disabled@devtable.com")
    disabled_user.verified = True
    disabled_user.enabled = False
    disabled_user.save()

    dtrobot = model.user.create_robot("dtrobot", new_user_1)
    dtrobot2 = model.user.create_robot("dtrobot2", new_user_1)

    new_user_2 = model.user.create_user("public", "password", "jacob.moshenko@gmail.com")
    new_user_2.verified = True
    new_user_2.save()

    new_user_3 = model.user.create_user("freshuser", "password", "jschorr+test@devtable.com")
    new_user_3.verified = True
    new_user_3.save()

    another_robot = model.user.create_robot("anotherrobot", new_user_3)

    new_user_4 = model.user.create_user("randomuser", "password", "no4@thanks.com")
    new_user_4.verified = True
    new_user_4.save()

    new_user_5 = model.user.create_user("unverified", "password", "no5@thanks.com")
    new_user_5.save()

    reader = model.user.create_user("reader", "password", "no1@thanks.com")
    reader.verified = True
    reader.save()

    creatoruser = model.user.create_user("creator", "password", "noc@thanks.com")
    creatoruser.verified = True
    creatoruser.save()

    outside_org = model.user.create_user("outsideorg", "password", "no2@thanks.com")
    outside_org.verified = True
    outside_org.save()

    model.notification.create_notification(
        "test_notification",
        new_user_1,
        metadata={"some": "value", "arr": [1, 2, 3], "obj": {"a": 1, "b": 2}},
    )

    from_date = datetime.utcnow()
    to_date = from_date + timedelta(hours=1)
    notification_metadata = {
        "from_date": formatdate(calendar.timegm(from_date.utctimetuple())),
        "to_date": formatdate(calendar.timegm(to_date.utctimetuple())),
        "reason": "database migration",
    }
    model.notification.create_notification(
        "maintenance", new_user_1, metadata=notification_metadata
    )

    __generate_repository(
        new_user_4,
        "randomrepo",
        "Random repo repository.",
        False,
        [],
        (4, [], ["latest", "prod"]),
    )

    simple_repo = __generate_repository(
        new_user_1,
        "simple",
        "Simple repository.",
        False,
        [],
        (4, [], ["latest", "prod"]),
    )

    # Add some labels to the latest tag's manifest.
    repo_ref = RepositoryReference.for_repo_obj(simple_repo)
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)
    assert manifest

    first_label = registry_model.create_manifest_label(manifest, "foo", "bar", "manifest")
    registry_model.create_manifest_label(manifest, "foo", "baz", "api")
    registry_model.create_manifest_label(manifest, "anotherlabel", "1234", "internal")
    registry_model.create_manifest_label(
        manifest, "jsonlabel", '{"hey": "there"}', "internal", "application/json"
    )

    label_metadata = {
        "key": "foo",
        "value": "bar",
        "id": first_label._db_id,
        "manifest_digest": manifest.digest,
    }

    logs_model.log_action(
        "manifest_label_add",
        new_user_1.username,
        performer=new_user_1,
        timestamp=datetime.now(),
        metadata=label_metadata,
        repository=simple_repo,
    )

    model.blob.initiate_upload(new_user_1.username, simple_repo.name, str(uuid4()), "local_us", {})
    model.notification.create_repo_notification(
        simple_repo, "repo_push", "quay_notification", {}, {}
    )

    __generate_repository(
        new_user_1,
        "sharedtags",
        "Shared tags repository",
        False,
        [(new_user_2, "read"), (dtrobot[0], "read")],
        (
            2,
            [
                (3, [], ["v2.0", "v2.1", "v2.2"]),
                (
                    1,
                    [(1, [(1, [], ["prod", "581a284"])], ["staging", "8423b58"]), (1, [], None)],
                    None,
                ),
            ],
            None,
        ),
    )

    __generate_repository(
        new_user_1,
        "history",
        "Historical repository.",
        False,
        [],
        (4, [(2, [], "#latest"), (3, [], "latest")], None),
    )

    __generate_repository(
        new_user_1,
        "complex",
        "Complex repository with many branches and tags.",
        False,
        [(new_user_2, "read"), (dtrobot[0], "read")],
        (
            2,
            [(3, [], "v2.0"), (1, [(1, [(2, [], ["prod"])], "staging"), (1, [], None)], None)],
            None,
        ),
    )

    __generate_repository(
        new_user_1,
        "gargantuan",
        None,
        False,
        [],
        (
            2,
            [
                (3, [], "v2.0"),
                (1, [(1, [(1, [], ["latest", "prod"])], "staging"), (1, [], None)], None),
                (20, [], "v3.0"),
                (5, [], "v4.0"),
                (1, [(1, [], "v5.0"), (1, [], "v6.0")], None),
            ],
            None,
        ),
    )

    trusted_repo = __generate_repository(
        new_user_1,
        "trusted",
        "Trusted repository.",
        False,
        [],
        (4, [], ["latest", "prod"]),
    )
    trusted_repo.trust_enabled = True
    trusted_repo.save()

    publicrepo = __generate_repository(
        new_user_2,
        "publicrepo",
        "Public repository pullable by the world.",
        True,
        [],
        (10, [], "latest"),
    )

    __generate_repository(outside_org, "coolrepo", "Some cool repo.", False, [], (5, [], "latest"))

    __generate_repository(
        new_user_1,
        "shared",
        "Shared repository, another user can write.",
        False,
        [(new_user_2, "write"), (reader, "read")],
        (5, [], "latest"),
    )

    __generate_repository(
        new_user_1,
        "text-full-repo",
        "This is a repository for testing text search",
        False,
        [(new_user_2, "write"), (reader, "read")],
        (5, [], "latest"),
    )

    building = __generate_repository(
        new_user_1,
        "building",
        "Empty repository which is building.",
        False,
        [(new_user_2, "write"), (reader, "read")],
        (0, [], None),
    )

    new_token = model.token.create_access_token(building, "write", "build-worker")

    trigger = model.build.create_build_trigger(
        building, "github", "123authtoken", new_user_1, pull_robot=dtrobot[0]
    )
    trigger.config = json.dumps(
        {
            "build_source": "jakedt/testconnect",
            "subdir": "",
            "dockerfile_path": "Dockerfile",
            "context": "/",
        }
    )
    trigger.save()

    repo = "ci.devtable.com:5000/%s/%s" % (building.namespace_user.username, building.name)
    job_config = {
        "repository": repo,
        "docker_tags": ["latest"],
        "build_subdir": "",
        "trigger_metadata": {
            "commit": "3482adc5822c498e8f7db2e361e8d57b3d77ddd9",
            "ref": "refs/heads/master",
            "default_branch": "master",
        },
    }

    model.repository.star_repository(new_user_1, simple_repo)

    record = model.repository.create_email_authorization_for_repo(
        new_user_1.username, "simple", "jschorr@devtable.com"
    )
    record.confirmed = True
    record.save()

    model.repository.create_email_authorization_for_repo(
        new_user_1.username, "simple", "jschorr+other@devtable.com"
    )

    build2 = model.build.create_repository_build(
        building,
        new_token,
        job_config,
        "68daeebd-a5b9-457f-80a0-4363b882f8ea",
        "build-name",
        trigger,
    )
    build2.uuid = "deadpork-dead-pork-dead-porkdeadpork"
    build2.save()

    build3 = model.build.create_repository_build(
        building,
        new_token,
        job_config,
        "f49d07f9-93da-474d-ad5f-c852107c3892",
        "build-name",
        trigger,
    )
    build3.uuid = "deadduck-dead-duck-dead-duckdeadduck"
    build3.save()

    build1 = model.build.create_repository_build(
        building, new_token, job_config, "701dcc3724fb4f2ea6c31400528343cd", "build-name", trigger
    )
    build1.uuid = "deadbeef-dead-beef-dead-beefdeadbeef"
    build1.save()

    org = model.organization.create_organization("buynlarge", "quay@devtable.com", new_user_1)
    org.stripe_id = TEST_STRIPE_ID
    org.save()

    liborg = model.organization.create_organization(
        "library", "quay+library@devtable.com", new_user_1
    )
    liborg.save()

    titiorg = model.organization.create_organization("titi", "quay+titi@devtable.com", new_user_1)
    titiorg.save()

    thirdorg = model.organization.create_organization(
        "sellnsmall", "quay+sell@devtable.com", new_user_1
    )
    thirdorg.save()

    model.user.create_robot("coolrobot", org)

    oauth_app_1 = model.oauth.create_application(
        org,
        "Some Test App",
        "http://localhost:8000",
        "http://localhost:8000/o2c.html",
        client_id="deadbeef",
    )

    model.oauth.create_application(
        org,
        "Some Other Test App",
        "http://quay.io",
        "http://localhost:8000/o2c.html",
        client_id="deadpork",
        description="This is another test application",
    )

    model.oauth.create_user_access_token(
        new_user_1, "deadbeef", "repo:admin", access_token="%s%s" % ("b" * 40, "c" * 40)
    )

    oauth_credential = Credential.from_string("dswfhasdf1")
    OAuthAuthorizationCode.create(
        application=oauth_app_1,
        code="Z932odswfhasdf1",
        scope="repo:admin",
        data='{"somejson": "goeshere"}',
        code_name="Z932odswfhasdf1Z932o",
        code_credential=oauth_credential,
    )

    model.user.create_robot("neworgrobot", org)

    ownerbot = model.user.create_robot("ownerbot", org)[0]
    creatorbot = model.user.create_robot("creatorbot", org)[0]

    owners = model.team.get_organization_team("buynlarge", "owners")
    owners.description = "Owners have unfetterd access across the entire org."
    owners.save()

    org_repo = __generate_repository(
        org,
        "orgrepo",
        "Repository owned by an org.",
        False,
        [(outside_org, "read")],
        (4, [], ["latest", "prod"]),
    )

    __generate_repository(
        org,
        "anotherorgrepo",
        "Another repository owned by an org.",
        False,
        [],
        (4, [], ["latest", "prod"]),
    )

    creators = model.team.create_team("creators", org, "creator", "Creators of orgrepo.")

    reader_team = model.team.create_team("readers", org, "member", "Readers of orgrepo.")
    model.team.add_or_invite_to_team(new_user_1, reader_team, outside_org)
    model.permission.set_team_repo_permission(
        reader_team.name, org_repo.namespace_user.username, org_repo.name, "read"
    )

    model.team.add_user_to_team(new_user_2, reader_team)
    model.team.add_user_to_team(reader, reader_team)
    model.team.add_user_to_team(ownerbot, owners)
    model.team.add_user_to_team(creatorbot, creators)
    model.team.add_user_to_team(creatoruser, creators)

    sell_owners = model.team.get_organization_team("sellnsmall", "owners")
    sell_owners.description = "Owners have unfettered access across the entire org."
    sell_owners.save()

    model.team.add_user_to_team(new_user_4, sell_owners)

    sync_config = {"group_dn": "cn=Test-Group,ou=Users", "group_id": "somegroupid"}
    synced_team = model.team.create_team("synced", org, "member", "Some synced team.")
    model.team.set_team_syncing(synced_team, "ldap", sync_config)

    another_synced_team = model.team.create_team("synced", thirdorg, "member", "Some synced team.")
    model.team.set_team_syncing(another_synced_team, "ldap", {"group_dn": "cn=Test-Group,ou=Users"})

    __generate_repository(
        new_user_1,
        "superwide",
        None,
        False,
        [],
        [
            (10, [], "latest2"),
            (2, [], "latest3"),
            (2, [(1, [], "latest11"), (2, [], "latest12")], "latest4"),
            (2, [], "latest5"),
            (2, [], "latest6"),
            (2, [], "latest7"),
            (2, [], "latest8"),
            (2, [], "latest9"),
            (2, [], "latest10"),
            (2, [], "latest13"),
            (2, [], "latest14"),
            (2, [], "latest15"),
            (2, [], "latest16"),
            (2, [], "latest17"),
            (2, [], "latest18"),
        ],
    )

    mirror_repo = __generate_repository(
        new_user_1,
        "mirrored",
        "Mirrored repository.",
        False,
        [(dtrobot[0], "write"), (dtrobot2[0], "write")],
        (4, [], ["latest", "prod"]),
    )
    mirror_rule = model.repo_mirror.create_mirroring_rule(mirror_repo, ["latest", "3.3*"])
    mirror_args = (mirror_repo, mirror_rule, dtrobot[0], "quay.io/coreos/etcd", 60 * 60 * 24)
    mirror_kwargs = {
        "external_registry_username": "fakeusername",
        "external_registry_password": "fakepassword",
        "external_registry_config": {},
        "is_enabled": True,
        "sync_start_date": datetime.utcnow(),
    }
    mirror = model.repo_mirror.enable_mirroring_for_repository(*mirror_args, **mirror_kwargs)

    read_only_repo = __generate_repository(
        new_user_1,
        "readonly",
        "Read-Only Repo.",
        False,
        [],
        (4, [], ["latest", "prod"]),
    )
    read_only_repo.state = RepositoryState.READ_ONLY
    read_only_repo.save()

    model.permission.add_prototype_permission(
        org, "read", activating_user=new_user_1, delegate_user=new_user_2
    )
    model.permission.add_prototype_permission(
        org, "read", activating_user=new_user_1, delegate_team=reader_team
    )
    model.permission.add_prototype_permission(
        org, "write", activating_user=new_user_2, delegate_user=new_user_1
    )

    today = datetime.today()
    week_ago = today - timedelta(6)
    six_ago = today - timedelta(5)
    four_ago = today - timedelta(4)
    yesterday = datetime.combine(date.today(), datetime.min.time()) - timedelta(hours=6)

    __generate_service_key(
        "kid1", "somesamplekey", new_user_1, today, ServiceKeyApprovalType.SUPERUSER
    )
    __generate_service_key(
        "kid2",
        "someexpiringkey",
        new_user_1,
        week_ago,
        ServiceKeyApprovalType.SUPERUSER,
        today + timedelta(days=14),
    )

    __generate_service_key("kid3", "unapprovedkey", new_user_1, today, None)

    __generate_service_key(
        "kid4",
        "autorotatingkey",
        new_user_1,
        six_ago,
        ServiceKeyApprovalType.KEY_ROTATION,
        today + timedelta(days=1),
        rotation_duration=timedelta(hours=12).total_seconds(),
    )

    __generate_service_key(
        "kid5",
        "key for another service",
        new_user_1,
        today,
        ServiceKeyApprovalType.SUPERUSER,
        today + timedelta(days=14),
        service="different_sample_service",
    )

    __generate_service_key(
        "kid6",
        "someexpiredkey",
        new_user_1,
        week_ago,
        ServiceKeyApprovalType.SUPERUSER,
        today - timedelta(days=1),
    )

    __generate_service_key(
        "kid7",
        "somewayexpiredkey",
        new_user_1,
        week_ago,
        ServiceKeyApprovalType.SUPERUSER,
        today - timedelta(days=30),
    )

    # Add the test pull key as pre-approved for local and unittest registry testing.
    # Note: this must match the private key found in the local/test config.
    _TEST_JWK = {
        "e": "AQAB",
        "kty": "RSA",
        "n": "yqdQgnelhAPMSeyH0kr3UGePK9oFOmNfwD0Ymnh7YYXr21VHWwyM2eVW3cnLd9KXywDFtGSe9oFDbnOuMCdUowdkBcaHju-isbv5KEbNSoy_T2Rip-6L0cY63YzcMJzv1nEYztYXS8wz76pSK81BKBCLapqOCmcPeCvV9yaoFZYvZEsXCl5jjXN3iujSzSF5Z6PpNFlJWTErMT2Z4QfbDKX2Nw6vJN6JnGpTNHZvgvcyNX8vkSgVpQ8DFnFkBEx54PvRV5KpHAq6AsJxKONMo11idQS2PfCNpa2hvz9O6UZe-eIX8jPo5NW8TuGZJumbdPT_nxTDLfCqfiZboeI0Pw",
    }

    key = model.service_keys.create_service_key(
        "test_service_key", "test_service_key", "quay", _TEST_JWK, {}, None
    )

    model.service_keys.approve_service_key(
        key.kid,
        ServiceKeyApprovalType.SUPERUSER,
        notes="Test service key for local/test registry testing",
    )

    # Add an app specific token.
    token = model.appspecifictoken.create_token(new_user_1, "some app")
    token.token_name = "a" * 60
    token.token_secret = "b" * 60
    token.save()

    logs_model.log_action(
        "org_create_team",
        org.username,
        performer=new_user_1,
        timestamp=week_ago,
        metadata={"team": "readers"},
    )

    logs_model.log_action(
        "org_set_team_role",
        org.username,
        performer=new_user_1,
        timestamp=week_ago,
        metadata={"team": "readers", "role": "read"},
    )

    logs_model.log_action(
        "create_repo",
        org.username,
        performer=new_user_1,
        repository=org_repo,
        timestamp=week_ago,
        metadata={"namespace": org.username, "repo": "orgrepo"},
    )

    logs_model.log_action(
        "change_repo_permission",
        org.username,
        performer=new_user_2,
        repository=org_repo,
        timestamp=six_ago,
        metadata={"username": new_user_1.username, "repo": "orgrepo", "role": "admin"},
    )

    logs_model.log_action(
        "change_repo_permission",
        org.username,
        performer=new_user_1,
        repository=org_repo,
        timestamp=six_ago,
        metadata={"username": new_user_2.username, "repo": "orgrepo", "role": "read"},
    )

    logs_model.log_action(
        "add_repo_accesstoken",
        org.username,
        performer=new_user_1,
        repository=org_repo,
        timestamp=four_ago,
        metadata={"repo": "orgrepo", "token": "deploytoken"},
    )

    logs_model.log_action(
        "push_repo",
        org.username,
        performer=new_user_2,
        repository=org_repo,
        timestamp=today,
        metadata={"username": new_user_2.username, "repo": "orgrepo"},
    )

    logs_model.log_action(
        "pull_repo",
        org.username,
        performer=new_user_2,
        repository=org_repo,
        timestamp=today,
        metadata={"username": new_user_2.username, "repo": "orgrepo"},
    )

    logs_model.log_action(
        "pull_repo",
        org.username,
        repository=org_repo,
        timestamp=today,
        metadata={"token": "sometoken", "token_code": "somecode", "repo": "orgrepo"},
    )

    logs_model.log_action(
        "delete_tag",
        org.username,
        performer=new_user_2,
        repository=org_repo,
        timestamp=today,
        metadata={"username": new_user_2.username, "repo": "orgrepo", "tag": "sometag"},
    )

    logs_model.log_action(
        "pull_repo",
        org.username,
        repository=org_repo,
        timestamp=today,
        metadata={"token_code": "somecode", "repo": "orgrepo"},
    )

    logs_model.log_action(
        "pull_repo",
        new_user_2.username,
        repository=publicrepo,
        timestamp=yesterday,
        metadata={"token_code": "somecode", "repo": "publicrepo"},
    )

    logs_model.log_action(
        "build_dockerfile",
        new_user_1.username,
        repository=building,
        timestamp=today,
        metadata={
            "repo": "building",
            "namespace": new_user_1.username,
            "trigger_id": trigger.uuid,
            "config": json.loads(trigger.config),
            "service": trigger.service.name,
        },
    )

    model.message.create(
        [
            {
                "content": "We love you, Quay customers!",
                "severity": "info",
                "media_type": "text/plain",
            }
        ]
    )

    model.message.create(
        [
            {
                "content": "This is a **development** install of Quay",
                "severity": "warning",
                "media_type": "text/markdown",
            }
        ]
    )

    fake_queue = WorkQueue("fakequeue", tf)
    fake_queue.put(["canonical", "job", "name"], "{}")

    model.user.create_user_prompt(new_user_4, "confirm_username")

    for to_count in Repository.select():
        model.repositoryactioncount.count_repository_actions(to_count, datetime.utcnow())
        model.repositoryactioncount.update_repository_score(to_count)


WHITELISTED_EMPTY_MODELS = [
    "DeletedNamespace",
    "DeletedRepository",
    "ManifestChild",
    "NamespaceGeoRestriction",
    "RepoMirrorConfig",
    "RepoMirrorRule",
    "ImageStorageSignature",
    "DerivedStorageForImage",
    "TorrentInfo",
    "LogEntry",
    "LogEntry2",
    "ManifestSecurityStatus",
    "ManifestLegacyImage",
    "Image",
]


def find_models_missing_data():
    # As a sanity check we are going to make sure that all db tables have some data, unless explicitly
    # whitelisted.
    models_missing_data = set()
    for one_model in all_models:
        if one_model in appr_classes:
            continue

        try:
            one_model.select().get()
        except one_model.DoesNotExist:
            if one_model.__name__ not in WHITELISTED_EMPTY_MODELS and not is_deprecated_model(
                one_model
            ):
                models_missing_data.add(one_model.__name__)

    return models_missing_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the test database.")
    parser.add_argument("--simple", action="store_true")
    args = parser.parse_args()

    log_level = os.environ.get("LOGGING_LEVEL", getattr(logging, app.config["LOGGING_LEVEL"]))
    logging.basicConfig(level=log_level)

    if not IS_TESTING_REAL_DATABASE and not isinstance(db.obj, SqliteDatabase):
        raise RuntimeError("Attempted to initialize production database!")

    if os.environ.get("SKIP_DB_SCHEMA", "").lower() != "true":
        initialize_database()

    populate_database(args.simple)

    if not args.simple:
        models_missing_data = find_models_missing_data()
        if models_missing_data:
            logger.warning("The following models do not have any data: %s", models_missing_data)
