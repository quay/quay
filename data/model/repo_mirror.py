import re

from datetime import datetime, timedelta

from peewee import IntegrityError, fn, JOIN
from jsonschema import ValidationError

from data.database import (
    RepoMirrorConfig,
    RepoMirrorRule,
    RepoMirrorRuleType,
    RepoMirrorStatus,
    RepositoryState,
    Repository,
    uuid_generator,
    db_transaction,
    User,
)
from data.fields import DecryptedValue
from data.model import DataModelException
from util.names import parse_robot_username


# TODO: Move these to the configuration
MAX_SYNC_RETRIES = 3
MAX_SYNC_DURATION = 60 * 60 * 2  # 2 Hours


def get_eligible_mirrors():
    """
    Returns the RepoMirrorConfig that are ready to run now.

    This includes those that are:
    1. Not currently syncing but whose start time is in the past
    2. Status of "sync now"
    3. Currently marked as syncing but whose expiration time is in the past
    """
    now = datetime.utcnow()
    immediate_candidates_filter = (RepoMirrorConfig.sync_status == RepoMirrorStatus.SYNC_NOW) & (
        RepoMirrorConfig.sync_expiration_date >> None
    )

    ready_candidates_filter = (
        (RepoMirrorConfig.sync_start_date <= now)
        & (RepoMirrorConfig.sync_retries_remaining > 0)
        & (RepoMirrorConfig.sync_status != RepoMirrorStatus.SYNCING)
        & (RepoMirrorConfig.sync_expiration_date >> None)
        & (RepoMirrorConfig.is_enabled == True)
    )

    expired_candidates_filter = (
        (RepoMirrorConfig.sync_start_date <= now)
        & (RepoMirrorConfig.sync_retries_remaining > 0)
        & (RepoMirrorConfig.sync_status == RepoMirrorStatus.SYNCING)
        & (RepoMirrorConfig.sync_expiration_date <= now)
        & (RepoMirrorConfig.is_enabled == True)
    )

    return (
        RepoMirrorConfig.select()
        .join(Repository)
        .where(Repository.state == RepositoryState.MIRROR)
        .where(immediate_candidates_filter | ready_candidates_filter | expired_candidates_filter)
        .order_by(RepoMirrorConfig.sync_start_date.asc())
    )


def get_max_id_for_repo_mirror_config():
    """
    Gets the maximum id for repository mirroring.
    """
    return RepoMirrorConfig.select(fn.Max(RepoMirrorConfig.id)).scalar()


def get_min_id_for_repo_mirror_config():
    """
    Gets the minimum id for a repository mirroring.
    """
    return RepoMirrorConfig.select(fn.Min(RepoMirrorConfig.id)).scalar()


def claim_mirror(mirror):
    """
    Attempt to create an exclusive lock on the RepoMirrorConfig and return it.

    If unable to create the lock, `None` will be returned.
    """

    # Attempt to update the RepoMirrorConfig to mark it as "claimed"
    now = datetime.utcnow()
    expiration_date = now + timedelta(seconds=MAX_SYNC_DURATION)
    query = RepoMirrorConfig.update(
        sync_status=RepoMirrorStatus.SYNCING,
        sync_expiration_date=expiration_date,
        sync_transaction_id=uuid_generator(),
    ).where(
        RepoMirrorConfig.id == mirror.id,
        RepoMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
    )

    # If the update was successful, then it was claimed. Return the updated instance.
    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)

    return None  # Another process must have claimed the mirror faster.


def release_mirror(mirror, sync_status):
    """
    Return a mirror to the queue and update its status.

    Upon success, move next sync to be at the next interval in the future. Failures remain with
    current date to ensure they are picked up for repeat attempt. After MAX_SYNC_RETRIES, the next
    sync will be moved ahead as if it were a success. This is to allow a daily sync, for example, to
    retry the next day. Without this, users would need to manually run syncs to clear failure state.
    """
    if sync_status == RepoMirrorStatus.FAIL:
        retries = max(0, mirror.sync_retries_remaining - 1)

    if sync_status == RepoMirrorStatus.SUCCESS or retries < 1:
        now = datetime.utcnow()
        delta = now - mirror.sync_start_date
        delta_seconds = (delta.days * 24 * 60 * 60) + delta.seconds
        next_start_date = now + timedelta(
            seconds=mirror.sync_interval - (delta_seconds % mirror.sync_interval)
        )
        retries = MAX_SYNC_RETRIES
    else:
        next_start_date = mirror.sync_start_date

    query = RepoMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_status=sync_status,
        sync_start_date=next_start_date,
        sync_expiration_date=None,
        sync_retries_remaining=retries,
    ).where(
        RepoMirrorConfig.id == mirror.id,
        RepoMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
    )

    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)

    # Unable to release Mirror. Has it been claimed by another process?
    return None


def expire_mirror(mirror):
    """
    Set the mirror to synchronize ASAP and reset its failure count.
    """

    # Set the next-sync date to now
    # TODO: Verify the `where` conditions would not expire a currently syncing mirror.
    query = RepoMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_expiration_date=datetime.utcnow(),
        sync_retries_remaining=MAX_SYNC_RETRIES,
    ).where(
        RepoMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
        RepoMirrorConfig.id == mirror.id,
        RepoMirrorConfig.state != RepoMirrorStatus.SYNCING,
    )

    # Fetch and return the latest updates
    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)

    # Unable to update expiration date. Perhaps another process has claimed it?
    return None  # TODO: Raise some Exception?


def create_mirroring_rule(repository, rule_value, rule_type=RepoMirrorRuleType.TAG_GLOB_CSV):
    """
    Create a RepoMirrorRule for a given Repository.
    """

    if rule_type != RepoMirrorRuleType.TAG_GLOB_CSV:
        raise ValidationError("validation failed: rule_type must be TAG_GLOB_CSV")

    if not isinstance(rule_value, list) or len(rule_value) < 1:
        raise ValidationError(
            "validation failed: rule_value for TAG_GLOB_CSV must be a list with at least one rule"
        )

    rule = RepoMirrorRule.create(repository=repository, rule_type=rule_type, rule_value=rule_value)
    return rule


def enable_mirroring_for_repository(
    repository,
    root_rule,
    internal_robot,
    external_reference,
    sync_interval,
    external_registry_username=None,
    external_registry_password=None,
    external_registry_config=None,
    is_enabled=True,
    sync_start_date=None,
):
    """
    Create a RepoMirrorConfig and set the Repository to the MIRROR state.
    """
    assert internal_robot.robot

    namespace, _ = parse_robot_username(internal_robot.username)
    if namespace != repository.namespace_user.username:
        raise DataModelException("Cannot use robot for mirroring")

    with db_transaction():
        # Create the RepoMirrorConfig
        try:
            username = (
                DecryptedValue(external_registry_username) if external_registry_username else None
            )
            password = (
                DecryptedValue(external_registry_password) if external_registry_password else None
            )
            mirror = RepoMirrorConfig.create(
                repository=repository,
                root_rule=root_rule,
                is_enabled=is_enabled,
                internal_robot=internal_robot,
                external_reference=external_reference,
                external_registry_username=username,
                external_registry_password=password,
                external_registry_config=external_registry_config or {},
                sync_interval=sync_interval,
                sync_start_date=sync_start_date or datetime.utcnow(),
            )
        except IntegrityError:
            return RepoMirrorConfig.get(repository=repository)

        # Change Repository state to mirroring mode as needed
        if repository.state != RepositoryState.MIRROR:
            query = Repository.update(state=RepositoryState.MIRROR).where(
                Repository.id == repository.id
            )
            if not query.execute():
                raise DataModelException("Could not change the state of the repository")

        return mirror


def update_sync_status(mirror, sync_status):
    """
    Update the sync status.
    """
    query = RepoMirrorConfig.update(
        sync_transaction_id=uuid_generator(), sync_status=sync_status
    ).where(
        RepoMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
        RepoMirrorConfig.id == mirror.id,
    )
    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)

    return None


def update_sync_status_to_sync_now(mirror):
    """
    This will change the sync status to SYNC_NOW and set the retries remaining to one, if it is less
    than one.

    None will be returned in cases where this is not possible, such as if the mirror is in the
    SYNCING state.
    """

    if mirror.sync_status == RepoMirrorStatus.SYNCING:
        return None

    retries = max(mirror.sync_retries_remaining, 1)

    query = RepoMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_status=RepoMirrorStatus.SYNC_NOW,
        sync_expiration_date=None,
        sync_retries_remaining=retries,
    ).where(
        RepoMirrorConfig.id == mirror.id,
        RepoMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
    )

    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)

    return None


def update_sync_status_to_cancel(mirror):
    """
    If the mirror is SYNCING, it will be force-claimed (ignoring existing transaction id), and the
    state will set to NEVER_RUN.

    None will be returned in cases where this is not possible, such as if the mirror is not in the
    SYNCING state.
    """

    if (
        mirror.sync_status != RepoMirrorStatus.SYNCING
        and mirror.sync_status != RepoMirrorStatus.SYNC_NOW
    ):
        return None

    query = RepoMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_status=RepoMirrorStatus.NEVER_RUN,
        sync_expiration_date=None,
    ).where(RepoMirrorConfig.id == mirror.id)

    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)

    return None


def update_with_transaction(mirror, **kwargs):
    """
    Helper function which updates a Repository's RepoMirrorConfig while also rolling its
    sync_transaction_id for locking purposes.
    """

    # RepoMirrorConfig attributes which can be modified
    mutable_attributes = (
        "is_enabled",
        "mirror_type",
        "external_reference",
        "external_registry_username",
        "external_registry_password",
        "external_registry_config",
        "sync_interval",
        "sync_start_date",
        "sync_expiration_date",
        "sync_retries_remaining",
        "sync_status",
        "sync_transaction_id",
    )

    # Key-Value map of changes to make
    filtered_kwargs = {key: kwargs.pop(key) for key in mutable_attributes if key in kwargs}

    # Roll the sync_transaction_id to a new value
    filtered_kwargs["sync_transaction_id"] = uuid_generator()

    # Generate the query to perform the updates
    query = RepoMirrorConfig.update(filtered_kwargs).where(
        RepoMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
        RepoMirrorConfig.id == mirror.id,
    )

    # Apply the change(s) and return the object if successful
    if query.execute():
        return RepoMirrorConfig.get_by_id(mirror.id)
    else:
        return None


def get_mirror(repository):
    """
    Return the RepoMirrorConfig associated with the given Repository, or None if it doesn't exist.
    """
    try:
        return (
            RepoMirrorConfig.select(RepoMirrorConfig, User, RepoMirrorRule)
            .join(User, JOIN.LEFT_OUTER)
            .switch(RepoMirrorConfig)
            .join(RepoMirrorRule)
            .where(RepoMirrorConfig.repository == repository)
            .get()
        )
    except RepoMirrorConfig.DoesNotExist:
        return None


def robot_has_mirror(robot):
    """
    Check whether the given robot is being used by any mirrors.
    """
    try:
        RepoMirrorConfig.get(internal_robot=robot)
        return True
    except RepoMirrorConfig.DoesNotExist:
        return False


def enable_mirror(repository):
    """
    Enables a RepoMirrorConfig.
    """
    mirror = get_mirror(repository)
    return bool(update_with_transaction(mirror, is_enabled=True))


def disable_mirror(repository):
    """
    Disables a RepoMirrorConfig.
    """
    mirror = get_mirror(repository)
    return bool(update_with_transaction(mirror, is_enabled=False))


def delete_mirror(repository):
    """
    Delete a Repository Mirroring configuration.
    """
    raise NotImplementedError("TODO: Not Implemented")


def change_remote(repository, remote_repository):
    """
    Update the external repository for Repository Mirroring.
    """
    mirror = get_mirror(repository)
    updates = {"external_reference": remote_repository}
    return bool(update_with_transaction(mirror, **updates))


def change_credentials(repository, username, password):
    """
    Update the credentials used to access the remote repository.
    """
    mirror = get_mirror(repository)
    updates = {
        "external_registry_username": username,
        "external_registry_password": password,
    }
    return bool(update_with_transaction(mirror, **updates))


def change_username(repository, username):
    """
    Update the Username used to access the external repository.
    """
    mirror = get_mirror(repository)
    return bool(update_with_transaction(mirror, external_registry_username=username))


def change_sync_interval(repository, interval):
    """
    Update the interval at which a repository will be synchronized.
    """
    mirror = get_mirror(repository)
    return bool(update_with_transaction(mirror, sync_interval=interval))


def change_sync_start_date(repository, dt):
    """
    Specify when the repository should be synchronized next.
    """
    mirror = get_mirror(repository)
    return bool(update_with_transaction(mirror, sync_start_date=dt))


def change_root_rule(repository, rule):
    """
    Specify which rule should be used for repository mirroring.
    """
    assert rule.repository == repository
    mirror = get_mirror(repository)
    return bool(update_with_transaction(mirror, root_rule=rule))


def change_sync_status(repository, sync_status):
    """
    Change Repository's mirroring status.
    """
    mirror = get_mirror(repository)
    return update_with_transaction(mirror, sync_status=sync_status)


def change_retries_remaining(repository, retries_remaining):
    """
    Change the number of retries remaining for mirroring a repository.
    """
    mirror = get_mirror(repository)
    return update_with_transaction(mirror, sync_retries_remaining=retries_remaining)


def change_external_registry_config(repository, config_updates):
    """
    Update the 'external_registry_config' with the passed in fields.

    Config has:
    verify_tls: True|False
    proxy: JSON fields 'http_proxy', 'https_proxy', andn 'no_proxy'
    """
    mirror = get_mirror(repository)
    external_registry_config = mirror.external_registry_config

    if "verify_tls" in config_updates:
        external_registry_config["verify_tls"] = config_updates["verify_tls"]

    if "proxy" in config_updates:
        proxy_updates = config_updates["proxy"]
        for key in ("http_proxy", "https_proxy", "no_proxy"):
            if key in config_updates["proxy"]:
                if "proxy" not in external_registry_config:
                    external_registry_config["proxy"] = {}
                else:
                    external_registry_config["proxy"][key] = proxy_updates[key]

    return update_with_transaction(mirror, external_registry_config=external_registry_config)


def get_mirroring_robot(repository):
    """
    Return the robot used for mirroring.

    Returns None if the repository does not have an associated RepoMirrorConfig or the robot does
    not exist.
    """
    mirror = get_mirror(repository)
    if mirror:
        return mirror.internal_robot

    return None


def set_mirroring_robot(repository, robot):
    """
    Sets the mirroring robot for the repository.
    """
    assert robot.robot
    namespace, _ = parse_robot_username(robot.username)
    if namespace != repository.namespace_user.username:
        raise DataModelException("Cannot use robot for mirroring")

    mirror = get_mirror(repository)
    mirror.internal_robot = robot
    mirror.save()


# -------------------- Mirroring Rules --------------------------#


def validate_rule(rule_type, rule_value):
    if rule_type != RepoMirrorRuleType.TAG_GLOB_CSV:
        raise ValidationError("validation failed: rule_type must be TAG_GLOB_CSV")

    if not rule_value or not isinstance(rule_value, list) or len(rule_value) < 1:
        raise ValidationError(
            "validation failed: rule_value for TAG_GLOB_CSV must be a list with at least one rule"
        )


def create_rule(
    repository,
    rule_value,
    rule_type=RepoMirrorRuleType.TAG_GLOB_CSV,
    left_child=None,
    right_child=None,
):
    """
    Create a new Rule for mirroring a Repository.
    """

    validate_rule(rule_type, rule_value)

    rule_kwargs = {
        "repository": repository,
        "rule_value": rule_value,
        "rule_type": rule_type,
        "left_child": left_child,
        "right_child": right_child,
    }
    rule = RepoMirrorRule.create(**rule_kwargs)
    return rule


def list_rules(repository):
    """
    Returns all RepoMirrorRules associated with a Repository.
    """
    rules = RepoMirrorRule.select().where(RepoMirrorRule.repository == repository).all()
    return rules


def get_root_rule(repository):
    """
    Return the primary mirroring Rule.
    """
    mirror = get_mirror(repository)
    try:
        rule = RepoMirrorRule.get(repository=repository)
        return rule
    except RepoMirrorRule.DoesNotExist:
        return None


def change_rule(repository, rule_type, rule_value):
    """
    Update the value of an existing rule.
    """

    validate_rule(rule_type, rule_value)

    mirrorRule = get_root_rule(repository)
    if not mirrorRule:
        raise ValidationError("validation failed: rule not found")

    query = RepoMirrorRule.update(rule_value=rule_value).where(RepoMirrorRule.id == mirrorRule.id)
    return query.execute()
