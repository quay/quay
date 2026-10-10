#!/usr/bin/env python3
"""
Regenerate plans/rewrite/generated/rewrite_snapshot.md from tracker artifacts.
"""

import csv
import re
from collections import Counter
from pathlib import Path


def load_csv_rows(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main():
    generated_dir = Path("plans/rewrite/generated")
    route_rows = load_csv_rows(generated_dir / "route_migration_tracker.csv")
    worker_rows = load_csv_rows(generated_dir / "worker_migration_tracker.csv")
    runtime_rows = load_csv_rows(generated_dir / "runtime_component_mapping.csv")
    worker_ver_rows = load_csv_rows(generated_dir / "worker_verification_checklist.csv")
    route_auth_rows = load_csv_rows(generated_dir / "route_auth_verification_checklist.csv")

    route_family_counts = Counter(r["route_family"] for r in route_rows)
    runtime_waves = Counter(r["execution_wave"] for r in runtime_rows)
    worker_status_counts = Counter(r["verification_status"] for r in worker_ver_rows)
    route_auth_counts = Counter(r["verification_status"] for r in route_auth_rows)

    route_with_batch = sum(1 for r in route_auth_rows if r.get("signoff_batch"))
    worker_with_batch = sum(1 for r in worker_ver_rows if r.get("signoff_batch"))
    route_batches = len({r["signoff_batch"] for r in route_auth_rows if r.get("signoff_batch")})
    worker_batches = len({r["signoff_batch"] for r in worker_ver_rows if r.get("signoff_batch")})

    decision_log = Path("plans/rewrite/decision_log.md").read_text()
    decision_statuses = re.findall(r"\| `D-\d+` \| ([^|]+) \|", decision_log)
    status_counts = Counter(s.strip().lower() for s in decision_statuses)
    decisions_approved = status_counts.get("approved", 0)
    decisions_pending = sum(
        count for status, count in status_counts.items() if status != "approved"
    )

    route_family_order = [
        "api-v1",
        "keys",
        "oauth1",
        "oauth2",
        "other",
        "realtime",
        "registry-v1",
        "registry-v2",
        "secscan",
        "web",
        "webhooks",
        "well-known",
    ]

    lines = [
        "# Rewrite Snapshot",
        "",
        "Generated status snapshot across migration trackers.",
        "",
        f"- route rows: {len(route_rows)}",
        f"- worker/process rows: {len(worker_rows)}",
        f"- runtime component rows: {len(runtime_rows)}",
        "",
        "## Route families",
    ]
    for family in route_family_order:
        if family in route_family_counts:
            lines.append(f"- `{family}`: {route_family_counts[family]}")

    lines.extend(
        [
            "",
            "## Worker verification",
        ]
    )
    for status in ["retired-approved", "verified-source-anchored"]:
        if status in worker_status_counts:
            lines.append(f"- `{status}`: {worker_status_counts[status]}")

    lines.extend(
        [
            "",
            "## Route auth verification",
            f"- `source-anchored-needs-review`: {route_auth_counts.get('source-anchored-needs-review', 0)}",
            f"- `verified-source-anchored`: {route_auth_counts.get('verified-source-anchored', 0)}",
            "",
            "## Runtime waves",
        ]
    )
    for wave in ["W1", "W2", "W3"]:
        if wave in runtime_waves:
            lines.append(f"- `{wave}`: {runtime_waves[wave]}")

    lines.extend(
        [
            "",
            "## Signoff batch coverage",
            f"- route rows with batch tags: {route_with_batch}/{len(route_auth_rows)}",
            f"- worker rows with batch tags: {worker_with_batch}/{len(worker_ver_rows)}",
            f"- distinct route batches: {route_batches}",
            f"- distinct worker batches: {worker_batches}",
            "",
            "## Decision status",
            f"- decisions pending: {decisions_pending}",
            f"- decisions approved: {decisions_approved}",
            "",
            "## Notes",
            "- `web=66` in `route_family_counts.md` (raw `@web.route` rows) reconciles to tracker `web=65` (method-level family rows) per `route_family_counts.md` reconciliation notes.",
            "",
        ]
    )

    (generated_dir / "rewrite_snapshot.md").write_text("\n".join(lines))
    print("Wrote plans/rewrite/generated/rewrite_snapshot.md")


if __name__ == "__main__":
    main()
