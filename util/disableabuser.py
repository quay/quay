import argparse

from datetime import datetime

from app import tf
from data import model
from data.model import db_transaction
from data.database import (
    QueueItem,
    Repository,
    RepositoryBuild,
    RepositoryBuildTrigger,
    RepoMirrorConfig,
)
from data.queue import WorkQueue


def ask_disable_namespace(username, queue_name):
    user = model.user.get_namespace_user(username)
    if user is None:
        raise Exception("Unknown user or organization %s" % username)

    if not user.enabled:
        print("NOTE: Namespace %s is already disabled" % username)

    queue_prefix = "%s/%s/%%" % (queue_name, username)
    existing_queue_item_count = (
        QueueItem.select()
        .where(QueueItem.queue_name ** queue_prefix)
        .where(
            QueueItem.available == 1,
            QueueItem.retries_remaining > 0,
            QueueItem.processing_expires > datetime.now(),
        )
        .count()
    )

    repository_trigger_count = (
        RepositoryBuildTrigger.select()
        .join(Repository)
        .where(Repository.namespace_user == user)
        .count()
    )

    print("=============================================")
    print("For namespace %s" % username)
    print("=============================================")

    print("User %s has email address %s" % (username, user.email))
    print("User %s has %s queued builds in their namespace" % (username, existing_queue_item_count))
    print("User %s has %s build triggers in their namespace" % (username, repository_trigger_count))

    confirm_msg = (
        "Would you like to disable this user and delete their triggers and builds? [y/N]> "
    )
    letter = str(input(confirm_msg))
    if letter.lower() != "y":
        print("Action canceled")
        return

    print("=============================================")

    triggers = []
    count_removed = 0
    with db_transaction():
        user.enabled = False
        user.save()

        repositories_query = Repository.select().where(Repository.namespace_user == user)
        if len(repositories_query.clone()):
            builds = list(
                RepositoryBuild.select().where(
                    RepositoryBuild.repository << list(repositories_query)
                )
            )

            triggers = list(
                RepositoryBuildTrigger.select().where(
                    RepositoryBuildTrigger.repository << list(repositories_query)
                )
            )

            mirrors = list(
                RepoMirrorConfig.select().where(
                    RepoMirrorConfig.repository << list(repositories_query)
                )
            )

            # Delete all builds for the user's repositories.
            if builds:
                RepositoryBuild.delete().where(RepositoryBuild.id << builds).execute()

            # Delete all build triggers for the user's repositories.
            if triggers:
                RepositoryBuildTrigger.delete().where(
                    RepositoryBuildTrigger.id << triggers
                ).execute()

            # Delete all mirrors for the user's repositories.
            if mirrors:
                RepoMirrorConfig.delete().where(RepoMirrorConfig.id << mirrors).execute()

            # Delete all queue items for the user's namespace.
            dockerfile_build_queue = WorkQueue(queue_name, tf, has_namespace=True)
            count_removed = dockerfile_build_queue.delete_namespaced_items(user.username)

    info = (user.username, len(triggers), count_removed, len(mirrors))
    print(
        "Namespace %s disabled, %s triggers deleted, %s queued builds removed, %s mirrors deleted"
        % info
    )
    return user


def disable_abusing_user(username, queue_name):
    if not username:
        raise Exception("Must enter a username")

    # Disable the namespace itself.
    user = ask_disable_namespace(username, queue_name)

    # If an organization, ask if all team members should be disabled as well.
    if user.organization:
        members = model.organization.get_organization_member_set(user)
        for membername in members:
            ask_disable_namespace(membername, queue_name)


parser = argparse.ArgumentParser(description="Disables a user abusing the build system")
parser.add_argument("username", help="The username of the abuser")
parser.add_argument(
    "queuename",
    help="The name of the dockerfile build queue "
    + "(e.g. `dockerfilebuild` or `dockerfilebuildstaging`)",
)
args = parser.parse_args()
disable_abusing_user(args.username, args.queuename)
