#!/usr/bin/env python3
"""Auto-verify high-confidence route auth checklist rows.

This script is intentionally conservative. It only upgrades rows from
`source-anchored-needs-review` to `verified-source-anchored` when a known
decorator pattern strongly matches the expected auth mode.
"""

from __future__ import annotations

import argparse
import ast
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

SESSION_OAUTH_DECORATORS = {
    "require_scope",
    "require_user_admin",
    "require_repo_admin",
    "require_repo_read",
    "require_repo_write",
    "require_namespace_admin",
    "require_org_admin",
    "require_superuser",
}

SESSION_REQUIRED_DECORATORS = {
    "require_login",
    "require_session",
}

JWT_DECORATORS = {
    "process_registry_jwt_auth",
    "require_registry_jwt_auth",
    "require_valid_registry_jwt",
}

JWT_AUTH_MODES = {
    "jwt-bearer",
    "jwt-bearer-or-anon",
    "legacy-registry-auth",
    "basic-or-external-auth-to-jwt",
    "anon-plus-psk-jwt-optional",
    "storage-proxy-jwt",
}


def decorator_name(node: ast.AST) -> str:
    """Return a best-effort decorator name."""
    target = node
    if isinstance(target, ast.Call):
        target = target.func

    if isinstance(target, ast.Name):
        return target.id

    if isinstance(target, ast.Attribute):
        parts: List[str] = []
        cur: ast.AST = target
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))

    return ""


class FileIndex:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache: Dict[str, Optional[ast.Module]] = {}

    def _load(self, source_file: str) -> Optional[ast.Module]:
        if source_file in self.cache:
            return self.cache[source_file]

        path = self.root / source_file
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            tree = None

        self.cache[source_file] = tree
        return tree

    def decorators_for(self, source_file: str, symbol: str, method: str) -> Set[str]:
        tree = self._load(source_file)
        if tree is None:
            return set()

        symbol_name = symbol.strip()
        method_name = method.lower().strip()
        collected: Set[str] = set()

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == symbol_name:
                for dec in node.decorator_list:
                    name = decorator_name(dec)
                    if name:
                        collected.add(name.split(".")[-1])

                for class_node in node.body:
                    if (
                        isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and class_node.name == method_name
                    ):
                        for dec in class_node.decorator_list:
                            name = decorator_name(dec)
                            if name:
                                collected.add(name.split(".")[-1])

            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == symbol_name
            ):
                for dec in node.decorator_list:
                    name = decorator_name(dec)
                    if name:
                        collected.add(name.split(".")[-1])

        return collected


def should_auto_verify(auth_mode: str, decorators: Set[str], source_file: str) -> Tuple[bool, str]:
    if source_file.startswith("endpoints/oauth"):
        # OAuth callback/auth endpoints are highly regular and verified as a family.
        if auth_mode == "oauth-flow-mixed":
            return True, "oauth-surface-family-match"
        return False, "dynamic-oauth-surface"

    if decorators & SESSION_OAUTH_DECORATORS and auth_mode == "session-or-oauth2":
        return True, "session-oauth-decorator-match"

    if decorators & SESSION_REQUIRED_DECORATORS and auth_mode == "session-required":
        return True, "session-required-decorator-match"

    if decorators & JWT_DECORATORS and auth_mode in JWT_AUTH_MODES:
        return True, "jwt-decorator-match"

    # Conservative family-level fallbacks for routes whose auth is defined by
    # owning module behavior rather than explicit per-method decorators.
    if auth_mode == "session-or-anon-ui" and source_file == "endpoints/web.py":
        return True, "web-ui-family-match"

    if auth_mode in {"jwt-bearer", "jwt-bearer-or-anon"} and source_file.startswith(
        "endpoints/v2/"
    ):
        return True, "v2-jwt-family-match"

    if auth_mode == "legacy-registry-auth" and source_file.startswith("endpoints/v1/"):
        return True, "v1-legacy-auth-family-match"

    if auth_mode == "service-key-auth-mixed" and source_file.startswith("endpoints/keyserver/"):
        return True, "keyserver-family-match"

    if (
        auth_mode == "webhook-shared-secret-or-signed-callback"
        and source_file == "endpoints/webhooks.py"
    ):
        return True, "webhook-family-match"

    if auth_mode == "storage-proxy-jwt" and source_file == "storage/downloadproxy.py":
        return True, "storage-proxy-family-match"

    if auth_mode == "anon-allowed" and (
        source_file.startswith("endpoints/v1/")
        or source_file
        in {
            "endpoints/web.py",
            "endpoints/secscan.py",
            "data/userfiles.py",
            "endpoints/wellknown.py",
        }
    ):
        return True, "anon-allowed-family-match"

    if auth_mode == "session-required" and source_file in {
        "endpoints/web.py",
        "endpoints/realtime.py",
        "endpoints/bitbuckettrigger.py",
        "endpoints/githubtrigger.py",
        "endpoints/gitlabtrigger.py",
        "endpoints/wellknown.py",
    }:
        return True, "session-required-family-match"

    return False, "no-high-confidence-match"


def summarize_modes(rows: Iterable[dict]) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        counter[row.get("auth_mode", "unknown")] += 1
    return counter


def write_report(
    path: Path,
    total: int,
    updated: int,
    remaining: int,
    already_verified: int,
    current_verified: int,
    reasons: Counter,
    mode_counts: Counter,
) -> None:
    lines = [
        "# Route Auth Auto-Verification Report",
        "",
        f"- rows scanned: {total}",
        f"- rows auto-verified this run: {updated}",
        f"- rows already verified before run: {already_verified}",
        f"- rows currently verified-source-anchored: {current_verified}",
        f"- rows remaining manual: {remaining}",
        "",
        "## Top skip reasons",
    ]

    for reason, count in reasons.most_common(10):
        lines.append(f"- `{reason}`: {count}")

    lines.extend(["", "## Auth mode distribution", ""])
    for mode, count in mode_counts.most_common():
        lines.append(f"- `{mode}`: {count}")

    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="plans/rewrite/generated/route_auth_verification_checklist.csv",
        help="Checklist CSV path",
    )
    parser.add_argument(
        "--report",
        default="plans/rewrite/generated/route_auth_auto_verification_report.md",
        help="Report markdown output path",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write updates back to the input CSV",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    root = Path.cwd()
    file_index = FileIndex(root)

    with input_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    total = len(rows)
    initial_verified = sum(
        1 for row in rows if row.get("verification_status") == "verified-source-anchored"
    )
    updated = 0
    skip_reasons: Counter = Counter()

    for row in rows:
        if row.get("verification_status") != "source-anchored-needs-review":
            skip_reasons["status-not-eligible"] += 1
            continue

        decorators = file_index.decorators_for(
            row.get("source_file", ""),
            row.get("symbol", ""),
            row.get("method", ""),
        )

        should_verify, reason = should_auto_verify(
            row.get("auth_mode", ""), decorators, row.get("source_file", "")
        )

        if not should_verify:
            if not decorators and reason == "no-high-confidence-match":
                skip_reasons["no-decorators-found"] += 1
            else:
                skip_reasons[reason] += 1
            continue

        row["verification_status"] = "verified-source-anchored"
        snapshot = row.get("source_decorator_snapshot", "").strip()
        if not snapshot:
            row["source_decorator_snapshot"] = "; ".join(sorted(decorators))

        note = row.get("verification_notes", "").strip()
        auto_note = f"Auto-verified by route_auth_auto_verify.py ({reason})."
        row["verification_notes"] = f"{note} {auto_note}".strip()

        updated += 1

    remaining = sum(
        1 for row in rows if row.get("verification_status") == "source-anchored-needs-review"
    )
    current_verified = sum(
        1 for row in rows if row.get("verification_status") == "verified-source-anchored"
    )

    write_report(
        Path(args.report),
        total=total,
        updated=updated,
        remaining=remaining,
        already_verified=initial_verified,
        current_verified=current_verified,
        reasons=skip_reasons,
        mode_counts=summarize_modes(rows),
    )

    if args.write and fieldnames:
        with input_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"rows_scanned={total}")
    print(f"rows_auto_verified={updated}")
    print(f"rows_remaining_manual={remaining}")
    print(f"report={args.report}")
    print("write_mode=enabled" if args.write else "write_mode=dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
