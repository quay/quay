# -*- coding: utf-8 -*-

from jsonschema import ValidationError

from data.database import RepoMirrorConfig, RepoMirrorStatus, User
from data import model
from data.model.repo_mirror import (
    create_mirroring_rule,
    get_eligible_mirrors,
    update_sync_status_to_cancel,
    MAX_SYNC_RETRIES,
    release_mirror,
)

from test.fixtures import *


def create_mirror_repo_robot(rules, repo_name="repo", external_registry_config=None):
    try:
        user = User.get(User.username == "mirror")
    except User.DoesNotExist:
        user = create_user_noverify("mirror", "mirror@example.com", email_required=False)

    try:
        robot = lookup_robot("mirror+robot")
    except model.InvalidRobotException:
        robot, _ = create_robot("robot", user)

    repo = model.repository.create_repository(
        "mirror", repo_name, None, repo_kind="image", visibility="public"
    )
    repo.save()

    rule = model.repo_mirror.create_mirroring_rule(repo, rules)

    mirror_kwargs = {
        "repository": repo,
        "root_rule": rule,
        "internal_robot": robot,
        "external_reference": "registry.example.com/namespace/repository",
        "sync_interval": timedelta(days=1).total_seconds(),
        "external_registry_config": external_registry_config,
    }
    mirror = model.repo_mirror.enable_mirroring_for_repository(**mirror_kwargs)
    mirror.sync_status = RepoMirrorStatus.NEVER_RUN
    mirror.sync_start_date = datetime.utcnow() - timedelta(days=1)
    mirror.sync_retries_remaining = 3
    mirror.save()

    return (mirror, repo)


def disable_existing_mirrors():
    mirrors = RepoMirrorConfig.select().execute()
    for mirror in mirrors:
        mirror.is_enabled = False
        mirror.save()


def test_eligible_oldest_first(initialized_db):
    """
    Eligible mirror candidates should be returned with the oldest (earliest created) first.
    """

    disable_existing_mirrors()
    mirror_first, repo_first = create_mirror_repo_robot(["updated", "created"], repo_name="first")
    mirror_second, repo_second = create_mirror_repo_robot(
        ["updated", "created"], repo_name="second"
    )
    mirror_third, repo_third = create_mirror_repo_robot(["updated", "created"], repo_name="third")

    candidates = get_eligible_mirrors()

    assert len(candidates) == 3
    assert candidates[0] == mirror_first
    assert candidates[1] == mirror_second
    assert candidates[2] == mirror_third


def test_eligible_includes_expired_syncing(initialized_db):
    """
    Mirrors that have an end time in the past are eligible even if their state indicates still
    syncing.
    """

    disable_existing_mirrors()
    mirror_first, repo_first = create_mirror_repo_robot(["updated", "created"], repo_name="first")
    mirror_second, repo_second = create_mirror_repo_robot(
        ["updated", "created"], repo_name="second"
    )
    mirror_third, repo_third = create_mirror_repo_robot(["updated", "created"], repo_name="third")
    mirror_fourth, repo_third = create_mirror_repo_robot(["updated", "created"], repo_name="fourth")

    mirror_second.sync_expiration_date = datetime.utcnow() - timedelta(hours=1)
    mirror_second.sync_status = RepoMirrorStatus.SYNCING
    mirror_second.save()

    mirror_fourth.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
    mirror_fourth.sync_status = RepoMirrorStatus.SYNCING
    mirror_fourth.save()

    candidates = get_eligible_mirrors()

    assert len(candidates) == 3
    assert candidates[0] == mirror_first
    assert candidates[1] == mirror_second
    assert candidates[2] == mirror_third


def test_eligible_includes_immediate(initialized_db):
    """
    Mirrors that are SYNC_NOW, regardless of starting time.
    """

    disable_existing_mirrors()
    mirror_first, repo_first = create_mirror_repo_robot(["updated", "created"], repo_name="first")
    mirror_second, repo_second = create_mirror_repo_robot(
        ["updated", "created"], repo_name="second"
    )
    mirror_third, repo_third = create_mirror_repo_robot(["updated", "created"], repo_name="third")
    mirror_fourth, repo_third = create_mirror_repo_robot(["updated", "created"], repo_name="fourth")
    mirror_future, _ = create_mirror_repo_robot(["updated", "created"], repo_name="future")
    mirror_past, _ = create_mirror_repo_robot(["updated", "created"], repo_name="past")

    mirror_future.sync_start_date = datetime.utcnow() + timedelta(hours=6)
    mirror_future.sync_status = RepoMirrorStatus.SYNC_NOW
    mirror_future.save()

    mirror_past.sync_start_date = datetime.utcnow() - timedelta(hours=6)
    mirror_past.sync_status = RepoMirrorStatus.SYNC_NOW
    mirror_past.save()

    mirror_fourth.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
    mirror_fourth.sync_status = RepoMirrorStatus.SYNCING
    mirror_fourth.save()

    candidates = get_eligible_mirrors()

    assert len(candidates) == 5
    assert candidates[0] == mirror_first
    assert candidates[1] == mirror_second
    assert candidates[2] == mirror_third
    assert candidates[3] == mirror_past
    assert candidates[4] == mirror_future


def test_create_rule_validations(initialized_db):
    mirror, repo = create_mirror_repo_robot(["updated", "created"], repo_name="first")

    with pytest.raises(ValidationError):
        create_mirroring_rule(repo, None)

    with pytest.raises(ValidationError):
        create_mirroring_rule(repo, "['tag1', 'tag2']")

    with pytest.raises(ValidationError):
        create_mirroring_rule(repo, ["tag1", "tag2"], rule_type=None)


def test_long_registry_passwords(initialized_db):
    """
    Verify that long passwords, such as Base64 JWT used by Redhat's Registry, work as expected.
    """
    MAX_PASSWORD_LENGTH = 1024

    username = "".join("a" for _ in range(MAX_PASSWORD_LENGTH))
    password = "".join("b" for _ in range(MAX_PASSWORD_LENGTH))
    assert len(username) == MAX_PASSWORD_LENGTH
    assert len(password) == MAX_PASSWORD_LENGTH

    repo = model.repository.get_repository("devtable", "mirrored")
    assert repo

    existing_mirror_conf = model.repo_mirror.get_mirror(repo)
    assert existing_mirror_conf

    assert model.repo_mirror.change_credentials(repo, username, password)

    updated_mirror_conf = model.repo_mirror.get_mirror(repo)
    assert updated_mirror_conf

    assert updated_mirror_conf.external_registry_username.decrypt() == username
    assert updated_mirror_conf.external_registry_password.decrypt() == password


def test_sync_status_to_cancel(initialized_db):
    """
    SYNCING and SYNC_NOW mirrors may be canceled, ending in NEVER_RUN.
    """

    disable_existing_mirrors()
    mirror, repo = create_mirror_repo_robot(["updated", "created"], repo_name="cancel")

    mirror.sync_status = RepoMirrorStatus.SYNCING
    mirror.save()
    updated = update_sync_status_to_cancel(mirror)
    assert updated is not None
    assert updated.sync_status == RepoMirrorStatus.NEVER_RUN

    mirror.sync_status = RepoMirrorStatus.SYNC_NOW
    mirror.save()
    updated = update_sync_status_to_cancel(mirror)
    assert updated is not None
    assert updated.sync_status == RepoMirrorStatus.NEVER_RUN

    mirror.sync_status = RepoMirrorStatus.FAIL
    mirror.save()
    updated = update_sync_status_to_cancel(mirror)
    assert updated is None

    mirror.sync_status = RepoMirrorStatus.NEVER_RUN
    mirror.save()
    updated = update_sync_status_to_cancel(mirror)
    assert updated is None

    mirror.sync_status = RepoMirrorStatus.SUCCESS
    mirror.save()
    updated = update_sync_status_to_cancel(mirror)
    assert updated is None


def test_release_mirror(initialized_db):
    """
    Mirrors that are SYNC_NOW, regardless of starting time.
    """

    disable_existing_mirrors()
    mirror, repo = create_mirror_repo_robot(["updated", "created"], repo_name="first")

    # mysql rounds the milliseconds on update so force that to happen now
    query = RepoMirrorConfig.update(sync_start_date=mirror.sync_start_date).where(
        RepoMirrorConfig.id == mirror.id
    )
    query.execute()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    original_sync_start_date = mirror.sync_start_date

    assert mirror.sync_retries_remaining == 3

    mirror = release_mirror(mirror, RepoMirrorStatus.FAIL)
    assert mirror.sync_retries_remaining == 2
    assert mirror.sync_start_date == original_sync_start_date

    mirror = release_mirror(mirror, RepoMirrorStatus.FAIL)
    assert mirror.sync_retries_remaining == 1
    assert mirror.sync_start_date == original_sync_start_date

    mirror = release_mirror(mirror, RepoMirrorStatus.FAIL)
    assert mirror.sync_retries_remaining == 3
    assert mirror.sync_start_date > original_sync_start_date


def test_repo_mirror_robot(initialized_db):
    mirror, _ = create_mirror_repo_robot(["updated", "created"], repo_name="first")
    assert mirror
    assert mirror.internal_robot
    assert model.repo_mirror.robot_has_mirror(mirror.internal_robot)
