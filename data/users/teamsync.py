import logging
import json

from data import model

logger = logging.getLogger(__name__)


MAX_TEAMS_PER_ITERATION = 500


def sync_teams_to_groups(authentication, stale_cutoff):
    """
    Performs team syncing by looking up any stale team(s) found, and performing the sync operation
    on them.
    """
    logger.debug("Looking up teams to sync to groups")

    sync_team_tried = set()
    while len(sync_team_tried) < MAX_TEAMS_PER_ITERATION:
        # Find a stale team.
        stale_team_sync = model.team.get_stale_team(stale_cutoff)
        if not stale_team_sync:
            logger.debug("No additional stale team found; sleeping")
            return

        # Make sure we don't try to reprocess a team on this iteration.
        if stale_team_sync.id in sync_team_tried:
            break

        sync_team_tried.add(stale_team_sync.id)

        # Sync the team.
        sync_successful = sync_team(authentication, stale_team_sync)
        if not sync_successful:
            return


def sync_team(authentication, stale_team_sync):
    """
    Performs synchronization of a team (as referenced by the TeamSync stale_team_sync).

    Returns True on success and False otherwise.
    """
    sync_config = json.loads(stale_team_sync.config)
    logger.info(
        "Syncing team `%s` under organization %s via %s (#%s)",
        stale_team_sync.team.name,
        stale_team_sync.team.organization.username,
        sync_config,
        stale_team_sync.team_id,
        extra={"team": stale_team_sync.team_id, "sync_config": sync_config},
    )

    # Load all the existing members of the team in Quay that are bound to the auth service.
    existing_users = model.team.get_federated_team_member_mapping(
        stale_team_sync.team, authentication.federated_service
    )

    logger.debug(
        "Existing membership of %s for team `%s` under organization %s via %s (#%s)",
        len(existing_users),
        stale_team_sync.team.name,
        stale_team_sync.team.organization.username,
        sync_config,
        stale_team_sync.team_id,
        extra={
            "team": stale_team_sync.team_id,
            "sync_config": sync_config,
            "existing_member_count": len(existing_users),
        },
    )

    # Load all the members of the team from the authenication system.
    (member_iterator, err) = authentication.iterate_group_members(sync_config)
    if err is not None:
        logger.error(
            "Got error when trying to iterate group members with config %s: %s", sync_config, err
        )
        return False

    # Collect all the members currently found in the group, adding them to the team as we go
    # along.
    group_membership = set()
    for (member_info, err) in member_iterator:
        if err is not None:
            logger.error("Got error when trying to construct a member: %s", err)
            continue

        # If the member is already in the team, nothing more to do.
        if member_info.username in existing_users:
            logger.debug(
                "Member %s already in team `%s` under organization %s via %s (#%s)",
                member_info.username,
                stale_team_sync.team.name,
                stale_team_sync.team.organization.username,
                sync_config,
                stale_team_sync.team_id,
                extra={
                    "team": stale_team_sync.team_id,
                    "sync_config": sync_config,
                    "member": member_info.username,
                },
            )

            group_membership.add(existing_users[member_info.username])
            continue

        # Retrieve the Quay user associated with the member info.
        (quay_user, err) = authentication.get_and_link_federated_user_info(
            member_info, internal_create=True
        )
        if err is not None:
            logger.error(
                "Could not link external user %s to an internal user: %s",
                member_info.username,
                err,
                extra={
                    "team": stale_team_sync.team_id,
                    "sync_config": sync_config,
                    "member": member_info.username,
                    "error": err,
                },
            )
            continue

        # Add the user to the membership set.
        group_membership.add(quay_user.id)

        # Add the user to the team.
        try:
            logger.info(
                "Adding member %s to team `%s` under organization %s via %s (#%s)",
                quay_user.username,
                stale_team_sync.team.name,
                stale_team_sync.team.organization.username,
                sync_config,
                stale_team_sync.team_id,
                extra={
                    "team": stale_team_sync.team_id,
                    "sync_config": sync_config,
                    "member": quay_user.username,
                },
            )

            model.team.add_user_to_team(quay_user, stale_team_sync.team)
        except model.UserAlreadyInTeam:
            # If the user is already present, nothing more to do for them.
            pass

    # Update the transaction and last_updated time of the team sync. Only if it matches
    # the current value will we then perform the deletion step.
    got_transaction_handle = model.team.update_sync_status(stale_team_sync)
    if not got_transaction_handle:
        # Another worker updated this team. Nothing more to do.
        logger.debug(
            "Another worker synced team `%s` under organization %s via %s (#%s)",
            stale_team_sync.team.name,
            stale_team_sync.team.organization.username,
            sync_config,
            stale_team_sync.team_id,
            extra={"team": stale_team_sync.team_id, "sync_config": sync_config},
        )
        return True

    # Delete any team members not found in the backing auth system.
    logger.debug(
        "Deleting stale members for team `%s` under organization %s via %s (#%s)",
        stale_team_sync.team.name,
        stale_team_sync.team.organization.username,
        sync_config,
        stale_team_sync.team_id,
        extra={"team": stale_team_sync.team_id, "sync_config": sync_config},
    )

    deleted = model.team.delete_members_not_present(stale_team_sync.team, group_membership)

    # Done!
    logger.info(
        "Finishing sync for team `%s` under organization %s via %s (#%s): %s deleted",
        stale_team_sync.team.name,
        stale_team_sync.team.organization.username,
        sync_config,
        stale_team_sync.team_id,
        deleted,
        extra={"team": stale_team_sync.team_id, "sync_config": sync_config},
    )
    return True
