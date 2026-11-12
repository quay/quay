#!/usr/bin/env python3
"""After CI passes on a PR, ask the pipeline controller to dispatch Prow and
publish ci/quay-deps-prow, which waits for the Prow GCS job on PRs that change
a Python dependency manifest.

Runs from a privileged workflow_run job: it reads PR metadata only and never
fetches or executes PR code.
"""

import http.client
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

CHECK_NAME = "ci/quay-deps-prow"
BOT_LOGIN = "github-actions[bot]"
RELEVANT_RE = re.compile(r"^(?:requirements(?:-build)?\.txt|constraints\.txt|pyproject\.toml)$")
ENROLLED_BASES = ("master",)
PROW_CONTEXT = "ci/prow/gcp-gcs"
POLL_SECONDS = 300
TIMEOUT_MINUTES = 300
RERUN_HINT = "After a passing /retest, re-run the Prow After CI workflow."


def select_pr(pulls, head_sha, head_repo, enrolled_bases):
    for pr in pulls:
        if (
            pr["head"]["sha"] == head_sha
            and (pr["head"]["repo"] or {}).get("full_name") == head_repo
            and pr["base"]["ref"] in enrolled_bases
        ):
            return pr
    return None


def ineligible_reason(pr, head_sha, enrolled_bases):
    if pr["state"] != "open":
        return f"PR #{pr['number']} is {pr['state']}"
    if pr["base"]["ref"] not in enrolled_bases:
        return f"PR #{pr['number']} base {pr['base']['ref']} is not enrolled"
    if pr["head"]["sha"] != head_sha:
        return f"PR #{pr['number']} HEAD moved to {pr['head']['sha']}"
    return None


def is_relevant(filenames):
    return any(RELEVANT_RE.match(name) for name in filenames)


def marker(head_sha):
    return f"<!-- prow-after-ci head={head_sha} -->"


def already_commented(comments, head_sha):
    return any(c["user"]["login"] == BOT_LOGIN and marker(head_sha) in c["body"] for c in comments)


def poll_outcome(pr, head_sha, statuses, context, timed_out):
    """Return (conclusion, summary) once the check can conclude, else None."""
    if pr["state"] != "open" or pr["head"]["sha"] != head_sha:
        return "cancelled", f"PR is no longer open at {head_sha}."
    status = next((s for s in statuses if s["context"] == context), None)
    state = status["state"] if status else None
    if state == "success":
        return "success", f"{context} passed."
    if state in ("failure", "error"):
        url = status.get("target_url") or "no link"
        return "failure", f"{context} reported {state}: {url}. {RERUN_HINT}"
    if timed_out:
        return "failure", f"No {context} result arrived before the timeout. {RERUN_HINT}"
    return None


class GitHub:
    def __init__(self, repo, token, api="https://api.github.com"):
        self.base = f"{api}/repos/{repo}"
        self.token = token

    def request(self, method, path, body=None):
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "quay-prow-after-ci",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)

    def paginate(self, path):
        sep = "&" if "?" in path else "?"
        items, page = [], 1
        while True:
            batch = self.request("GET", f"{path}{sep}per_page=100&page={page}")
            items.extend(batch)
            if len(batch) < 100:
                return items
            page += 1


def conclude(gh, check_id, conclusion, summary):
    gh.request(
        "PATCH",
        f"/check-runs/{check_id}",
        {
            "status": "completed",
            "conclusion": conclusion,
            "output": {"title": conclusion, "summary": summary},
        },
    )


def main():
    env = os.environ
    gh = GitHub(
        env["GITHUB_REPOSITORY"],
        env["GH_TOKEN"],
        env.get("GITHUB_API_URL", "https://api.github.com"),
    )
    head_sha = env["HEAD_SHA"]

    head = urllib.parse.quote(f"{env['HEAD_OWNER']}:{env['HEAD_BRANCH']}", safe="")
    pr = select_pr(
        gh.paginate(f"/pulls?state=open&head={head}"), head_sha, env["HEAD_REPO"], ENROLLED_BASES
    )
    if pr is None:
        print(
            f"No open PR to an enrolled base from {env['HEAD_REPO']} at {head_sha}; nothing to do."
        )
        return
    number = pr["number"]

    # A rename away from a manifest still changes the dependency set.
    relevant = is_relevant(
        name
        for f in gh.paginate(f"/pulls/{number}/files")
        for name in (f["filename"], f.get("previous_filename", ""))
    )

    if already_commented(gh.paginate(f"/issues/{number}/comments"), head_sha):
        print(f"/pipeline remaining already posted for {head_sha}.")
    else:
        reason = ineligible_reason(gh.request("GET", f"/pulls/{number}"), head_sha, ENROLLED_BASES)
        if reason:
            print(f"::notice::{reason}; skipping.")
            return
        body = f"/pipeline remaining\n{marker(head_sha)}"
        gh.request("POST", f"/issues/{number}/comments", {"body": body})

    if not relevant:
        gh.request(
            "POST",
            "/check-runs",
            {
                "name": CHECK_NAME,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": "success",
                "output": {
                    "title": "success",
                    "summary": "No Python dependency manifest changed; Prow result not required.",
                },
            },
        )
        return

    check_id = gh.request(
        "POST",
        "/check-runs",
        {
            "name": CHECK_NAME,
            "head_sha": head_sha,
            "status": "in_progress",
            "output": {"title": "waiting", "summary": f"Waiting for {PROW_CONTEXT}."},
        },
    )["id"]
    outcome = None
    try:
        deadline = time.monotonic() + TIMEOUT_MINUTES * 60
        while outcome is None:
            timed_out = time.monotonic() >= deadline
            try:
                outcome = poll_outcome(
                    gh.request("GET", f"/pulls/{number}"),
                    head_sha,
                    gh.request("GET", f"/commits/{head_sha}/status?per_page=100")["statuses"],
                    PROW_CONTEXT,
                    timed_out,
                )
            except (OSError, http.client.HTTPException) as err:
                if timed_out:
                    raise
                print(f"::warning::Polling failed ({err}); retrying.")
            if outcome is None:
                time.sleep(POLL_SECONDS)
    finally:
        if outcome is None:
            outcome = ("failure", "The waiter stopped before a result; re-run this workflow.")
        conclude(gh, check_id, *outcome)


if __name__ == "__main__":
    sys.exit(main())
