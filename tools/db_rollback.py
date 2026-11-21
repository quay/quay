#!/usr/bin/env python3
"""
Database Migration Rollback Tool for Quay

Automates safe Alembic downgrades with pre-flight checks, dry-run support,
and post-rollback verification. Designed to be run from inside a Quay
container or a pod with access to the Quay database.

Usage:
    # Show current migration state
    python tools/db_rollback.py --status

    # Show migration history (chain)
    python tools/db_rollback.py --history

    # Dry-run: preview the SQL that would be executed to roll back 1 migration
    python tools/db_rollback.py --dry-run --steps 1

    # Roll back the most recent migration
    python tools/db_rollback.py --steps 1

    # Roll back to a specific revision
    python tools/db_rollback.py --target <revision_id>

    # Roll back with explicit DB URI (overrides config.yaml)
    python tools/db_rollback.py --steps 1 --db-uri 'postgresql://user:pass@host/db'

Environment:
    PYTHONPATH must include the Quay repo root.
    Quay config.yaml must be loadable (or pass --db-uri).
"""

import argparse
import io
import logging
import os
import sys
import textwrap
from contextlib import redirect_stdout
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("db_rollback")

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")


def _get_alembic_config(db_uri_override=None):
    """Build an Alembic Config object, optionally overriding the DB URI."""
    from alembic.config import Config

    cfg = Config(os.path.abspath(ALEMBIC_INI))

    if db_uri_override:
        os.environ["QUAY_OVERRIDE_CONFIG"] = '{"DB_URI":"%s"}' % db_uri_override

    return cfg


def _get_engine(db_uri_override=None):
    """Create a SQLAlchemy engine using Quay's config chain."""
    if db_uri_override:
        from sqlalchemy import create_engine

        return create_engine(db_uri_override)

    from app import app

    db_url = app.config.get("DB_URI", "sqlite:///test/data/test.db")
    from sqlalchemy import create_engine

    return create_engine(db_url)


def _get_current_head(engine):
    """Read the current revision from alembic_version table."""
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = list(result)
        if not rows:
            return None
        return rows[0][0]


def _get_script_directory(cfg):
    """Return Alembic's ScriptDirectory for walking the revision graph."""
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(cfg)


def _table_exists(engine, table_name):
    """Check whether a table exists in the database."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status(engine, cfg):
    """Print the current database migration revision."""
    current = _get_current_head(engine)
    script = _get_script_directory(cfg)

    if current is None:
        logger.info("No alembic_version row found — database may be uninitialized.")
        return

    try:
        rev = script.get_revision(current)
        desc = rev.doc if rev else "(unknown)"
    except Exception:
        desc = "(unable to resolve)"

    head = script.get_current_head()
    at_head = current == head

    print()
    print(f"  Current revision : {current}")
    print(f"  Description      : {desc}")
    print(f"  Alembic head     : {head}")
    print(f"  Up to date       : {'YES' if at_head else 'NO — upgrades pending'}")
    print()


def cmd_history(engine, cfg):
    """Print the linear migration history (newest first)."""
    script = _get_script_directory(cfg)
    current = _get_current_head(engine)

    print()
    print("  Migration history (newest → oldest):")
    print("  " + "-" * 60)

    for rev in script.walk_revisions():
        marker = " ◀ current" if rev.revision == current else ""
        print(f"  {rev.revision}  {rev.doc}{marker}")

    print()


def cmd_dry_run(cfg, target):
    """
    Generate the SQL that a downgrade would execute without touching the DB.
    Uses Alembic's offline mode.
    """
    from alembic.command import downgrade

    print()
    print("  DRY-RUN — SQL that would be executed:")
    print("  " + "=" * 60)

    buf = io.StringIO()
    cfg.output_buffer = buf

    downgrade(cfg, target, sql=True)

    sql_output = buf.getvalue()
    if sql_output.strip():
        for line in sql_output.strip().splitlines():
            print(f"  {line}")
    else:
        print("  (no SQL generated — target may already be current)")

    print("  " + "=" * 60)
    print()


def cmd_downgrade(engine, cfg, target, skip_confirm=False):
    """
    Execute a downgrade with pre-flight checks, confirmation prompt, and
    post-rollback verification.
    """
    from alembic.command import downgrade

    current = _get_current_head(engine)
    script = _get_script_directory(cfg)

    if current is None:
        logger.error("Cannot downgrade: no alembic_version found.")
        sys.exit(1)

    head = script.get_current_head()

    # Resolve the target revision for display
    if target.startswith("-"):
        steps = int(target[1:])
        rev = script.get_revision(current)
        walk_target = current
        for _ in range(steps):
            r = script.get_revision(walk_target)
            if r is None or r.down_revision is None:
                logger.error("Cannot step back %d — only %d revisions above base.", steps, _)
                sys.exit(1)
            walk_target = r.down_revision
        target_display = walk_target
    else:
        target_display = target

    try:
        target_rev = script.get_revision(target_display)
        target_desc = target_rev.doc if target_rev else "(unknown)"
    except Exception:
        target_desc = "(unable to resolve)"

    # --- Pre-flight summary ---
    print()
    print("  " + "=" * 60)
    print("  DATABASE MIGRATION ROLLBACK")
    print("  " + "=" * 60)
    print(f"  Timestamp       : {datetime.utcnow().isoformat()}Z")
    print(f"  Current revision: {current}")
    print(f"  Target revision : {target_display}  ({target_desc})")
    print(f"  Alembic head    : {head}")
    print(
        f"  alembic_version : {'exists' if _table_exists(engine, 'alembic_version') else 'MISSING'}"
    )
    print("  " + "-" * 60)

    if current == target_display:
        logger.info("Database is already at the target revision. Nothing to do.")
        return

    # --- Confirmation ---
    if not skip_confirm:
        answer = input("\n  Proceed with downgrade? [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("Aborted by user.")
            sys.exit(0)

    # --- Execute ---
    logger.info("Starting downgrade to %s ...", target_display)

    try:
        downgrade(cfg, target)
    except Exception:
        logger.exception("Downgrade FAILED. Database may be in an inconsistent state.")
        logger.error("Investigate the alembic_version table and the schema manually.")
        sys.exit(2)

    # --- Post-rollback verification ---
    new_current = _get_current_head(engine)
    if new_current == target_display:
        logger.info("Downgrade succeeded.")
    else:
        logger.warning(
            "Unexpected state after downgrade: expected %s, got %s",
            target_display,
            new_current,
        )

    print()
    print(f"  Post-rollback revision: {new_current}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        description="Quay Database Migration Rollback Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              %(prog)s --status
              %(prog)s --history
              %(prog)s --dry-run --steps 1
              %(prog)s --steps 1
              %(prog)s --target 15f06d00c4b3
              %(prog)s --steps 1 --db-uri 'postgresql://user:pass@host/db'
              %(prog)s --steps 1 --yes   # skip confirmation prompt
        """
        ),
    )

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--status", action="store_true", help="Show current migration state")
    action.add_argument("--history", action="store_true", help="Show migration history")
    action.add_argument("--steps", type=int, metavar="N", help="Roll back N migrations")
    action.add_argument(
        "--target", type=str, metavar="REV", help="Roll back to a specific revision"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL without executing (requires --steps or --target)",
    )
    parser.add_argument(
        "--db-uri", type=str, metavar="URI", help="Override DB URI (instead of config.yaml)"
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cfg = _get_alembic_config(db_uri_override=args.db_uri)
    engine = _get_engine(db_uri_override=args.db_uri)

    if args.status:
        cmd_status(engine, cfg)
        return

    if args.history:
        cmd_history(engine, cfg)
        return

    # Determine target string for Alembic
    if args.steps:
        target = f"-{args.steps}"
    else:
        target = args.target

    if args.dry_run:
        cmd_dry_run(cfg, target)
    else:
        cmd_downgrade(engine, cfg, target, skip_confirm=args.yes)


if __name__ == "__main__":
    main()
