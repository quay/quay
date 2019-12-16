import argparse
import sys

from app import app
from data.database import Namespace, Repository, RepositoryPermission, Role
from data.model.permission import get_user_repo_permissions
from data.model.user import get_active_users, get_nonrobot_user

DESCRIPTION = """
Fix user repositories missing admin permissions for owning user.
"""

parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("users", nargs="*", help="Users to check")
parser.add_argument("-a", "--all", action="store_true", help="Check all users")
parser.add_argument("-n", "--dry-run", action="store_true", help="Don't act")

ADMIN = Role.get(name="admin")


def repos_for_namespace(namespace):
    return (
        Repository.select(Repository.id, Repository.name, Namespace.username)
        .join(Namespace)
        .where(Namespace.username == namespace)
    )


def has_admin(user, repo):
    perms = get_user_repo_permissions(user, repo)
    return any(p.role == ADMIN for p in perms)


def get_users(all_users=False, users_list=None):
    if all_users:
        return get_active_users(disabled=False)

    return list(map(get_nonrobot_user, users_list))


def ensure_admin(user, repos, dry_run=False):
    repos = [repo for repo in repos if not has_admin(user, repo)]

    for repo in repos:
        print(("User {} missing admin on: {}".format(user.username, repo.name)))

        if not dry_run:
            RepositoryPermission.create(user=user, repository=repo, role=ADMIN)
            print(("Granted {} admin on: {}".format(user.username, repo.name)))

    return len(repos)


def main():
    args = parser.parse_args()
    found = 0

    if not args.all and len(args.users) == 0:
        sys.exit("Need a list of users or --all")

    for user in get_users(all_users=args.all, users_list=args.users):
        if user is not None:
            repos = repos_for_namespace(user.username)
            found += ensure_admin(user, repos, dry_run=args.dry_run)

    print(("\nFound {} user repos missing admin" " permissions for owner.".format(found)))


if __name__ == "__main__":
    main()
