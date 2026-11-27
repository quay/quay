#!/usr/bin/env python3
"""
Export a fixed PromQL query set from a Prometheus server and summarize it.

    ci-metrics.py export --prom-url URL --start T --end T --step 30s \
        --queries .github/ci-metrics/queries.json --out quay-metrics
    ci-metrics.py summarize --in quay-metrics

export writes OUT/queries/<name>.json (raw query_range API output) and
OUT/meta.json. summarize reads only those files, so it also runs offline on a
downloaded quay-metrics artifact, and writes OUT/summary.md.
"""

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TIMEOUT_SECONDS = 60


def _get(prom_url, path, params):
    url = f"{prom_url.rstrip('/')}{path}?{urllib.parse.urlencode(params, doseq=True)}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body).get("error", body)
        except ValueError:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body}") from None


def up_gaps(result):
    """Runs of consecutive up==0 samples, per series."""
    gaps = []
    for series in result:
        instance = series["metric"].get("instance", "")
        start = prev = None
        for ts, value in series.get("values", []):
            if float(value) == 0:
                start = ts if start is None else start
                prev = ts
            elif start is not None:
                gaps.append({"instance": instance, "start": start, "end": prev})
                start = None
        if start is not None:
            gaps.append({"instance": instance, "start": start, "end": prev})
    return gaps


def restarts(result):
    """Changes in a process start time series; each change is one restart."""
    found = []
    for series in result:
        instance = series["metric"].get("instance", "")
        values = series.get("values", [])
        for (_, before), (_, after) in zip(values, values[1:]):
            if before != after:
                found.append({"instance": instance, "started": float(after)})
    return found


def _scrape_interval(prom_url):
    config = json.loads(_get(prom_url, "/api/v1/status/config", {}))["data"]["yaml"]
    # Prometheus renders the global block first, so the first match is the global value.
    match = re.search(r"^\s+scrape_interval: (\S+)", config, re.M)
    return match.group(1) if match else None


def export(args):
    with open(args.queries) as f:
        queries = json.load(f)
    os.makedirs(os.path.join(args.out, "queries"), exist_ok=True)
    window = {"start": args.start, "end": args.end, "step": args.step}
    meta = {
        "surface": "github-actions" if os.environ.get("GITHUB_RUN_ID") else "local",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "window": window,
        "prom_url": args.prom_url,
        "scrape_interval": None,
        "quay_series": None,
        "queries": {},
        "up_gaps": [],
        "restarts": [],
        "errors": [],
    }

    try:
        meta["scrape_interval"] = _scrape_interval(args.prom_url)
    except Exception as e:
        meta["errors"].append(f"scrape_interval: {e}")

    try:
        series = _get(
            args.prom_url,
            "/api/v1/series",
            {"match[]": '{__name__=~"quay_.+"}', "start": args.start, "end": args.end},
        )
        meta["quay_series"] = len(json.loads(series)["data"])
    except Exception as e:
        meta["errors"].append(f"quay_series: {e}")

    for q in queries:
        name = q["name"]
        info = meta["queries"][name] = {k: q[k] for k in ("expr", "unit") if k in q}
        try:
            raw = _get(args.prom_url, "/api/v1/query_range", dict(window, query=q["expr"]))
            result = json.loads(raw)["data"]["result"]
        except Exception as e:
            info["error"] = str(e)
            print(f"query {name} failed: {e}", file=sys.stderr)
            continue
        with open(os.path.join(args.out, "queries", f"{name}.json"), "wb") as f:
            f.write(raw)
        info["series"] = len(result)
        if name == "up":
            meta["up_gaps"] = up_gaps(result)
        elif name == "pushgateway_start_time":
            meta["restarts"] = restarts(result)

    with open(os.path.join(args.out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def _fmt(value, unit=None):
    if value is None:
        return "-"
    if unit == "bytes":
        # Step up at 1000, not 1024: 3 significant figures need an exponent only in [999.5, 1000).
        for prefix in ("", "Ki", "Mi", "Gi"):
            if value < 1000:
                break
            value /= 1024
        else:
            prefix = "Ti"
        return f"{value:.3g} {prefix}B"
    if unit == "seconds":
        return f"{value * 1000:.3g} ms" if value < 1 else f"{value:.3g} s"
    if unit == "timestamp":
        return _utc(value)
    if unit == "per_second":
        return f"{value:.3g}/s"
    if unit == "cores":
        return f"{value:.3g} cores"
    return f"{value:.4g}"


def _utc(ts):
    # PROMETHEUS_START is empty when the start step was skipped or failed before recording it.
    if ts == "":
        return "unknown"
    try:
        seconds = float(ts)
    except ValueError:
        # export also accepts RFC 3339, which is already readable.
        return ts
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarize(args):
    with open(os.path.join(args.dir, "meta.json")) as f:
        meta = json.load(f)

    lines = ["## Quay metrics", ""]
    if meta.get("quay_series") is None:
        lines += ["> **WARNING: quay_* series count unknown** (see errors in meta.json).", ""]
    elif not meta["quay_series"]:
        lines += [
            f"> **WARNING: {meta.get('quay_series')} quay_* series captured.** Quay processes "
            "pushed no metrics (TEST=true in the container, Pushgateway down, or no push yet).",
            "",
        ]
    lines += [
        f"Window {_utc(meta['window']['start'])} to {_utc(meta['window']['end'])} "
        f"(step {meta['window']['step']}, scrape interval {meta.get('scrape_interval')}), "
        f"{meta.get('quay_series')} quay_* series.",
        "",
        "| query | series | min | max | last |",
        "| --- | --- | --- | --- | --- |",
    ]

    up_result, start_result = [], []
    for name, info in meta["queries"].items():
        if "error" in info:
            lines.append(f"| {name} | error: {info['error']} | | | |")
            continue
        with open(os.path.join(args.dir, "queries", f"{name}.json")) as f:
            result = json.load(f)["data"]["result"]
        if name == "up":
            up_result = result
        elif name == "pushgateway_start_time":
            start_result = result
        samples, lasts = [], []
        for series in result:
            values = [float(v) for _, v in series.get("values", [])]
            values = [v for v in values if not math.isnan(v)]
            samples += values
            if values:
                lasts.append(values[-1])
        unit = info.get("unit")
        lines.append(
            f"| {name} | {len(result)} | {_fmt(min(samples, default=None), unit)} "
            f"| {_fmt(max(samples, default=None), unit)} | {_fmt(max(lasts, default=None), unit)} |"
        )
    lines += [
        "",
        "min and max span every sample; last is the highest final value of any series.",
        "",
    ]

    gaps = up_gaps(up_result)
    if gaps:
        lines.append("Scrape gaps (up == 0):")
        lines += [f"- {g['instance']}: {_utc(g['start'])} to {_utc(g['end'])}" for g in gaps]
    else:
        lines.append("Scrape gaps (up == 0): none")
    found = restarts(start_result)
    lines += ["", f"Pushgateway restarts: {len(found)}"]
    lines += [f"- {r['instance']}: started {_utc(r['started'])}" for r in found]
    if meta.get("errors"):
        lines += ["", "Export errors:"] + [f"- {e}" for e in meta["errors"]]

    with open(os.path.join(args.dir, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("export")
    p.add_argument("--prom-url", required=True)
    p.add_argument("--start", required=True, help="unix seconds or RFC 3339")
    p.add_argument("--end", required=True, help="unix seconds or RFC 3339")
    p.add_argument("--step", default="30s")
    p.add_argument("--queries", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=export)

    p = sub.add_parser("summarize")
    p.add_argument("--in", dest="dir", required=True)
    p.set_defaults(func=summarize)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
