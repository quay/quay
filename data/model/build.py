import json

from datetime import timedelta, datetime

from peewee import JOIN

from data.database import (
    BuildTriggerService,
    RepositoryBuildTrigger,
    Repository,
    Namespace,
    User,
    RepositoryBuild,
    BUILD_PHASE,
    db_random_func,
    UseThenDisconnect,
    TRIGGER_DISABLE_REASON,
)
from data.model import (
    InvalidBuildTriggerException,
    InvalidRepositoryBuildException,
    db_transaction,
    user as user_model,
    config,
)
from data.fields import DecryptedValue


PRESUMED_DEAD_BUILD_AGE = timedelta(days=15)
PHASES_NOT_ALLOWED_TO_CANCEL_FROM = (
    BUILD_PHASE.PUSHING,
    BUILD_PHASE.COMPLETE,
    BUILD_PHASE.ERROR,
    BUILD_PHASE.INTERNAL_ERROR,
)

ARCHIVABLE_BUILD_PHASES = [BUILD_PHASE.COMPLETE, BUILD_PHASE.ERROR, BUILD_PHASE.CANCELLED]


def update_build_trigger(trigger, config, auth_token=None, write_token=None):
    trigger.config = json.dumps(config or {})

    if auth_token is not None:
        trigger.secure_auth_token = DecryptedValue(auth_token)

    if write_token is not None:
        trigger.write_token = write_token

    trigger.save()


def create_build_trigger(repo, service_name, auth_token, user, pull_robot=None, config=None):
    service = BuildTriggerService.get(name=service_name)
    secure_auth_token = DecryptedValue(auth_token) if auth_token else None
    trigger = RepositoryBuildTrigger.create(
        repository=repo,
        service=service,
        secure_auth_token=secure_auth_token,
        connected_user=user,
        pull_robot=pull_robot,
        config=json.dumps(config or {}),
    )
    return trigger


def get_build_trigger(trigger_uuid):
    try:
        return (
            RepositoryBuildTrigger.select(
                RepositoryBuildTrigger, BuildTriggerService, Repository, Namespace
            )
            .join(BuildTriggerService)
            .switch(RepositoryBuildTrigger)
            .join(Repository)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .switch(RepositoryBuildTrigger)
            .join(User, on=(RepositoryBuildTrigger.connected_user == User.id))
            .where(RepositoryBuildTrigger.uuid == trigger_uuid)
            .get()
        )
    except RepositoryBuildTrigger.DoesNotExist:
        msg = "No build trigger with uuid: %s" % trigger_uuid
        raise InvalidBuildTriggerException(msg)


def list_build_triggers(namespace_name, repository_name):
    return (
        RepositoryBuildTrigger.select(RepositoryBuildTrigger, BuildTriggerService, Repository)
        .join(BuildTriggerService)
        .switch(RepositoryBuildTrigger)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == namespace_name, Repository.name == repository_name)
    )


def list_trigger_builds(namespace_name, repository_name, trigger_uuid, limit):
    return list_repository_builds(namespace_name, repository_name, limit).where(
        RepositoryBuildTrigger.uuid == trigger_uuid
    )


def get_repository_for_resource(resource_key):
    try:
        return (
            Repository.select(Repository, Namespace)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .switch(Repository)
            .join(RepositoryBuild)
            .where(RepositoryBuild.resource_key == resource_key)
            .get()
        )
    except Repository.DoesNotExist:
        return None


def _get_build_base_query():
    return (
        RepositoryBuild.select(
            RepositoryBuild,
            RepositoryBuildTrigger,
            BuildTriggerService,
            Repository,
            Namespace,
            User,
        )
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .switch(RepositoryBuild)
        .join(User, JOIN.LEFT_OUTER)
        .switch(RepositoryBuild)
        .join(RepositoryBuildTrigger, JOIN.LEFT_OUTER)
        .join(BuildTriggerService, JOIN.LEFT_OUTER)
        .order_by(RepositoryBuild.started.desc())
    )


def get_repository_build(build_uuid):
    try:
        return _get_build_base_query().where(RepositoryBuild.uuid == build_uuid).get()

    except RepositoryBuild.DoesNotExist:
        msg = "Unable to locate a build by id: %s" % build_uuid
        raise InvalidRepositoryBuildException(msg)


def list_repository_builds(
    namespace_name, repository_name, limit, include_inactive=True, since=None
):
    query = (
        _get_build_base_query()
        .where(Repository.name == repository_name, Namespace.username == namespace_name)
        .limit(limit)
    )

    if since is not None:
        query = query.where(RepositoryBuild.started >= since)

    if not include_inactive:
        query = query.where(
            RepositoryBuild.phase != BUILD_PHASE.ERROR,
            RepositoryBuild.phase != BUILD_PHASE.COMPLETE,
        )

    return query


def get_recent_repository_build(namespace_name, repository_name):
    query = list_repository_builds(namespace_name, repository_name, 1)
    try:
        return query.get()
    except RepositoryBuild.DoesNotExist:
        return None


def create_repository_build(
    repo,
    access_token,
    job_config_obj,
    dockerfile_id,
    display_name,
    trigger=None,
    pull_robot_name=None,
):
    pull_robot = None
    if pull_robot_name:
        pull_robot = user_model.lookup_robot(pull_robot_name)

    return RepositoryBuild.create(
        repository=repo,
        access_token=access_token,
        job_config=json.dumps(job_config_obj),
        display_name=display_name,
        trigger=trigger,
        resource_key=dockerfile_id,
        pull_robot=pull_robot,
    )


def get_pull_robot_name(trigger):
    if not trigger.pull_robot:
        return None

    return trigger.pull_robot.username


def _get_build_row(build_uuid):
    return RepositoryBuild.select().where(RepositoryBuild.uuid == build_uuid).get()


def update_phase_then_close(build_uuid, phase):
    """
    A function to change the phase of a build.
    """
    with UseThenDisconnect(config.app_config):
        try:
            build = _get_build_row(build_uuid)
        except RepositoryBuild.DoesNotExist:
            return False

        # Can't update a cancelled build
        if build.phase == BUILD_PHASE.CANCELLED:
            return False

        updated = (
            RepositoryBuild.update(phase=phase)
            .where(RepositoryBuild.id == build.id, RepositoryBuild.phase == build.phase)
            .execute()
        )

        return updated > 0


def create_cancel_build_in_queue(build_phase, build_queue_id, build_queue):
    """
    A function to cancel a build before it leaves the queue.
    """

    def cancel_build():
        cancelled = False

        if build_queue_id is not None:
            cancelled = build_queue.cancel(build_queue_id)

        if build_phase != BUILD_PHASE.WAITING:
            return False

        return cancelled

    return cancel_build


def create_cancel_build_in_manager(build_phase, build_uuid, build_canceller):
    """
    A function to cancel the build before it starts to push.
    """

    def cancel_build():
        if build_phase in PHASES_NOT_ALLOWED_TO_CANCEL_FROM:
            return False

        return build_canceller.try_cancel_build(build_uuid)

    return cancel_build


def cancel_repository_build(build, build_queue):
    """
    This tries to cancel the build returns true if request is successful false if it can't be
    cancelled.
    """
    from app import build_canceller
    from buildman.jobutil.buildjob import BuildJobNotifier

    cancel_builds = [
        create_cancel_build_in_queue(build.phase, build.queue_id, build_queue),
        create_cancel_build_in_manager(build.phase, build.uuid, build_canceller),
    ]
    for cancelled in cancel_builds:
        if cancelled():
            updated = update_phase_then_close(build.uuid, BUILD_PHASE.CANCELLED)
            if updated:
                BuildJobNotifier(build.uuid).send_notification("build_cancelled")

            return updated

    return False


def get_archivable_build():
    presumed_dead_date = datetime.utcnow() - PRESUMED_DEAD_BUILD_AGE

    candidates = (
        RepositoryBuild.select(RepositoryBuild.id)
        .where(
            (RepositoryBuild.phase << ARCHIVABLE_BUILD_PHASES)
            | (RepositoryBuild.started < presumed_dead_date),
            RepositoryBuild.logs_archived == False,
        )
        .limit(50)
        .alias("candidates")
    )

    try:
        found_id = (
            RepositoryBuild.select(candidates.c.id)
            .from_(candidates)
            .order_by(db_random_func())
            .get()
        )
        return RepositoryBuild.get(id=found_id)
    except RepositoryBuild.DoesNotExist:
        return None


def mark_build_archived(build_uuid):
    """
    Mark a build as archived, and return True if we were the ones who actually updated the row.
    """
    return (
        RepositoryBuild.update(logs_archived=True)
        .where(RepositoryBuild.uuid == build_uuid, RepositoryBuild.logs_archived == False)
        .execute()
    ) > 0


def toggle_build_trigger(trigger, enabled, reason=TRIGGER_DISABLE_REASON.USER_TOGGLED):
    """
    Toggles the enabled status of a build trigger.
    """
    trigger.enabled = enabled

    if not enabled:
        trigger.disabled_reason = RepositoryBuildTrigger.disabled_reason.get_id(reason)
        trigger.disabled_datetime = datetime.utcnow()

    trigger.save()


def update_trigger_disable_status(trigger, final_phase):
    """
    Updates the disable status of the given build trigger.

    If the build trigger had a failure, then the counter is increased and, if we've reached the
    limit, the trigger is automatically disabled. Otherwise, if the trigger succeeded, it's counter
    is reset. This ensures that triggers that continue to error are eventually automatically
    disabled.
    """
    with db_transaction():
        try:
            trigger = RepositoryBuildTrigger.get(id=trigger.id)
        except RepositoryBuildTrigger.DoesNotExist:
            # Already deleted.
            return

        # If the build completed successfully, then reset the successive counters.
        if final_phase == BUILD_PHASE.COMPLETE:
            trigger.successive_failure_count = 0
            trigger.successive_internal_error_count = 0
            trigger.save()
            return

        # Otherwise, increment the counters and check for trigger disable.
        if final_phase == BUILD_PHASE.ERROR:
            trigger.successive_failure_count = trigger.successive_failure_count + 1
            trigger.successive_internal_error_count = 0
        elif final_phase == BUILD_PHASE.INTERNAL_ERROR:
            trigger.successive_internal_error_count = trigger.successive_internal_error_count + 1

        # Check if we need to disable the trigger.
        failure_threshold = config.app_config.get("SUCCESSIVE_TRIGGER_FAILURE_DISABLE_THRESHOLD")
        error_threshold = config.app_config.get(
            "SUCCESSIVE_TRIGGER_INTERNAL_ERROR_DISABLE_THRESHOLD"
        )

        if failure_threshold and trigger.successive_failure_count >= failure_threshold:
            toggle_build_trigger(trigger, False, TRIGGER_DISABLE_REASON.BUILD_FALURES)
        elif error_threshold and trigger.successive_internal_error_count >= error_threshold:
            toggle_build_trigger(trigger, False, TRIGGER_DISABLE_REASON.INTERNAL_ERRORS)
        else:
            # Save the trigger changes.
            trigger.save()
