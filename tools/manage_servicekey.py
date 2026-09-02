import argparse
import sys
from datetime import datetime, timedelta

from app import app  # noqa: F401 (triggers config loading including QUAY_OVERRIDE_CONFIG)
from data.database import ServiceKey
from data.model import ServiceKeyDoesNotExist


def _get_key_direct(kid):
    """
    Direct lookup by kid, bypassing stale-expired filtering.
    """
    try:
        return ServiceKey.select().where(ServiceKey.kid == kid).get()
    except ServiceKey.DoesNotExist:
        return None


def expire_key(kid, grace_seconds):
    key = _get_key_direct(kid)
    if key is None:
        print("Key '%s' does not exist, nothing to do." % kid)
        return 0

    if key.service != "quay":
        print("Key '%s' belongs to service '%s', expected 'quay'." % (kid, key.service))
        return 1

    metadata = key.metadata if isinstance(key.metadata, dict) else {}
    if metadata.get("created_by") != "quay-operator-readonly":
        print(
            "Key '%s' is not operator-managed (created_by='%s'), refusing to expire."
            % (kid, metadata.get("created_by"))
        )
        return 1

    grace_deadline = datetime.utcnow() + timedelta(seconds=grace_seconds)
    if key.expiration_date is not None and key.expiration_date <= grace_deadline:
        print("Key '%s' already expiring within the requested grace window." % kid)
        return 0

    key.expiration_date = grace_deadline
    key.save()
    print("Key '%s' expiration set to %s." % (kid, grace_deadline.isoformat() + "Z"))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Manage Quay operator service keys")
    subparsers = parser.add_subparsers(dest="command")

    expire_parser = subparsers.add_parser("expire", help="Expire an operator-managed service key")
    expire_parser.add_argument("--kid", required=True, help="The key ID to expire")
    expire_parser.add_argument(
        "--grace-seconds",
        type=int,
        required=True,
        help="Seconds from now until the key expires",
    )

    args = parser.parse_args()

    if args.command == "expire":
        sys.exit(expire_key(args.kid, args.grace_seconds))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
