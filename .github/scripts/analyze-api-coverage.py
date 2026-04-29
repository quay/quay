#!/usr/bin/env python3
"""
Analyze API endpoint coverage from Jaeger/OTEL traces collected during E2E tests.

Compares observed (method, route) pairs from trace spans against the full catalog
of registered Flask routes, producing a coverage report in GitHub Step Summary
and a JSON artifact for trend tracking.

Environment variables:
    TRACES_FILE     - Path to Jaeger traces JSON (default: jaeger-traces/traces.json)
    COVERAGE_FILE   - Path to write JSON report (default: jaeger-traces/api-coverage.json)
    QUAY_API_URL    - Quay base URL for discovery endpoint (default: http://localhost:8080)
    GITHUB_STEP_SUMMARY - GitHub Actions step summary file (set automatically in CI)
"""

import json
import os
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

TRACES_FILE = os.environ.get("TRACES_FILE", "jaeger-traces/traces.json")
COVERAGE_FILE = os.environ.get("COVERAGE_FILE", "jaeger-traces/api-coverage.json")
QUAY_API_URL = os.environ.get("QUAY_API_URL", "http://localhost:8080")
COMMIT_SHA = os.environ.get("COMMIT_SHA", "unknown")

# V2 registry routes — small, stable set defined in endpoints/v2/.
# After normalization these become the canonical forms we compare against.
V2_ROUTES = [
    ("GET", "/v2/"),
    ("GET", "/v2/auth"),
    ("POST", "/v2/auth"),
    ("HEAD", "/v2/<repository>/blobs/<digest>"),
    ("GET", "/v2/<repository>/blobs/<digest>"),
    ("DELETE", "/v2/<repository>/blobs/<digest>"),
    ("POST", "/v2/<repository>/blobs/uploads/"),
    ("GET", "/v2/<repository>/blobs/uploads/<upload_uuid>"),
    ("PATCH", "/v2/<repository>/blobs/uploads/<upload_uuid>"),
    ("PUT", "/v2/<repository>/blobs/uploads/<upload_uuid>"),
    ("DELETE", "/v2/<repository>/blobs/uploads/<upload_uuid>"),
    ("GET", "/v2/<repository>/manifests/<manifest_ref>"),
    ("PUT", "/v2/<repository>/manifests/<manifest_ref>"),
    ("DELETE", "/v2/<repository>/manifests/<manifest_ref>"),
    ("GET", "/v2/_catalog"),
    ("GET", "/v2/<repository>/tags/list"),
    ("GET", "/v2/<repository>/referrers/<manifest_ref>"),
]


def normalize_route(route: str) -> str:
    """Normalize Flask/Swagger route patterns to a canonical form.

    Handles three formats:
      Flask with converters:  /<repopath:repository>/blobs/<regex("..."):digest>
      Swagger:                /api/v1/repository/{repository}
      Plain Flask:            /<repository>/blobs/<digest>

    All normalize to:         /<repository>/blobs/<digest>
    """
    # Strip Flask type converters first (before touching braces, since regex
    # patterns can contain {n,m} quantifiers that would be misinterpreted)
    route = re.sub(r"<[^>]*:(\w+)>", r"<\1>", route)
    # Swagger {param} -> <param>
    route = route.replace("{", "<").replace("}", ">")
    return route


def parse_traces(traces_file: str) -> tuple[set, dict]:
    """Extract observed (method, route) pairs and status codes from Jaeger traces.

    Returns:
        covered: set of (method, normalized_route) tuples
        status_matrix: dict of (method, normalized_route) -> set of status codes
    """
    with open(traces_file) as f:
        data = json.load(f)

    traces = data.get("data", [])
    if not traces:
        return set(), {}

    covered = set()
    status_matrix = defaultdict(set)

    for trace in traces:
        for span in trace.get("spans", []):
            tags = {t["key"]: t["value"] for t in span.get("tags", [])}

            route = tags.get("http.route")
            method = tags.get("http.method")
            if not route or not method:
                continue

            if method == "OPTIONS":
                continue

            normalized = normalize_route(route)
            key = (method, normalized)
            covered.add(key)

            status = tags.get("http.status_code")
            if status is not None:
                status_matrix[key].add(int(status))

    return covered, status_matrix


def fetch_api_v1_catalog(quay_url: str) -> set:
    """Fetch API v1 routes from the Quay discovery endpoint."""
    url = f"{quay_url}/api/v1/discovery?internal=true"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            discovery = json.loads(resp.read())
    except Exception as e:
        print(f"::warning::Could not fetch discovery endpoint: {e}")
        return set()

    catalog = set()
    for path, path_data in discovery.get("paths", {}).items():
        normalized = normalize_route(path)
        for method in ("get", "post", "put", "delete", "patch", "head"):
            if method in path_data:
                catalog.add((method.upper(), normalized))

    return catalog


def build_v2_catalog() -> set:
    """Return the hardcoded V2 registry route catalog."""
    return {(method, route) for method, route in V2_ROUTES}


def categorize_route(route: str) -> str:
    if route.startswith("/api/v1/"):
        return "api_v1"
    if route.startswith("/v2/"):
        return "v2_registry"
    return "other"


def build_report(catalog: set, covered: set, status_matrix: dict) -> dict:
    """Build the coverage report structure."""
    categories = defaultdict(lambda: {"covered": 0, "total": 0})

    for method, route in sorted(catalog):
        cat = categorize_route(route)
        categories[cat]["total"] += 1
        if (method, route) in covered:
            categories[cat]["covered"] += 1

    for cat_data in categories.values():
        total = cat_data["total"]
        cat_data["pct"] = round(cat_data["covered"] / total * 100, 1) if total else 0

    uncovered = sorted(catalog - covered)
    covered_in_catalog = sorted(catalog & covered)

    total_routes = len(catalog)
    total_covered = len(covered_in_catalog)
    total_pct = round(total_covered / total_routes * 100, 1) if total_routes else 0

    # Routes observed in traces but not in catalog (unexpected)
    extra = sorted(covered - catalog)
    extra_filtered = [(m, r) for m, r in extra if categorize_route(r) != "other"]

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_sha": COMMIT_SHA,
        "summary": {
            "api_v1": dict(categories["api_v1"]),
            "v2_registry": dict(categories["v2_registry"]),
            "total": {
                "covered": total_covered,
                "total": total_routes,
                "pct": total_pct,
            },
        },
        "covered": [
            {
                "method": m,
                "route": r,
                "category": categorize_route(r),
                "status_codes": sorted(status_matrix.get((m, r), [])),
            }
            for m, r in covered_in_catalog
        ],
        "uncovered": [
            {"method": m, "route": r, "category": categorize_route(r)} for m, r in uncovered
        ],
        "extra": [{"method": m, "route": r} for m, r in extra_filtered],
    }


def write_step_summary(report: dict, status_matrix: dict) -> str:
    """Generate GitHub Step Summary markdown."""
    lines = []
    lines.append("## API Endpoint Coverage")
    lines.append("")

    s = report["summary"]
    lines.append("| Category | Covered | Total | Coverage |")
    lines.append("|----------|---------|-------|----------|")

    for label, key in [("API v1", "api_v1"), ("V2 Registry", "v2_registry")]:
        cat = s.get(key, {})
        if cat.get("total", 0) > 0:
            lines.append(f"| {label} | {cat['covered']} | {cat['total']} | {cat['pct']}% |")

    t = s["total"]
    lines.append(f"| **Total** | **{t['covered']}** | **{t['total']}** | **{t['pct']}%** |")

    uncovered = report["uncovered"]
    if uncovered:
        lines.append("")
        lines.append(f"### Uncovered Routes ({len(uncovered)})")
        lines.append("")
        lines.append("| Method | Route | Category |")
        lines.append("|--------|-------|----------|")
        for entry in uncovered:
            lines.append(f"| {entry['method']} | `{entry['route']}` | {entry['category']} |")

    covered = report["covered"]
    routes_with_multiple_statuses = [e for e in covered if len(e["status_codes"]) > 1]
    if routes_with_multiple_statuses:
        lines.append("")
        lines.append(
            f"### Status Code Matrix ({len(routes_with_multiple_statuses)} routes with multiple status codes)"
        )
        lines.append("")
        lines.append("| Method | Route | Status Codes |")
        lines.append("|--------|-------|-------------|")
        for entry in routes_with_multiple_statuses:
            codes = ", ".join(str(c) for c in entry["status_codes"])
            lines.append(f"| {entry['method']} | `{entry['route']}` | {codes} |")

    extra = report.get("extra", [])
    if extra:
        lines.append("")
        lines.append(f"### Routes in Traces but Not in Catalog ({len(extra)})")
        lines.append("")
        lines.append("| Method | Route |")
        lines.append("|--------|-------|")
        for entry in extra:
            lines.append(f"| {entry['method']} | `{entry['route']}` |")

    lines.append("")
    return "\n".join(lines)


def main():
    if not os.path.isfile(TRACES_FILE) or os.path.getsize(TRACES_FILE) == 0:
        print("::warning::Traces file not found or empty — skipping API coverage analysis")
        return

    try:
        with open(TRACES_FILE) as f:
            probe = json.load(f)
        if "data" not in probe:
            print("::warning::Traces file missing 'data' key — skipping API coverage analysis")
            return
    except (json.JSONDecodeError, KeyError):
        print("::warning::Traces file is not valid JSON — skipping API coverage analysis")
        return

    trace_count = len(probe.get("data", []))
    print(f"Parsing {trace_count} traces from {TRACES_FILE}")

    covered, status_matrix = parse_traces(TRACES_FILE)
    print(f"Found {len(covered)} unique (method, route) pairs (excluding OPTIONS)")

    api_v1_catalog = fetch_api_v1_catalog(QUAY_API_URL)
    v2_catalog = build_v2_catalog()
    catalog = api_v1_catalog | v2_catalog

    if not catalog:
        print("::warning::Could not build route catalog — skipping coverage calculation")
        # Still write what we observed
        catalog = set()

    print(
        f"Route catalog: {len(api_v1_catalog)} API v1 + {len(v2_catalog)} V2 = {len(catalog)} total"
    )

    report = build_report(catalog, covered, status_matrix)

    os.makedirs(os.path.dirname(COVERAGE_FILE) or ".", exist_ok=True)
    with open(COVERAGE_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Coverage report written to {COVERAGE_FILE}")

    summary_md = write_step_summary(report, status_matrix)

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(summary_md)
        print("Step summary appended to GITHUB_STEP_SUMMARY")
    else:
        print(summary_md)

    s = report["summary"]["total"]
    print(f"\nAPI Coverage: {s['pct']}% ({s['covered']}/{s['total']})")


if __name__ == "__main__":
    main()
