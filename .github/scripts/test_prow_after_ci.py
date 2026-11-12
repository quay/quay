import importlib.util
import urllib.error
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "prow_after_ci", Path(__file__).with_name("prow-after-ci.py")
)
pac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pac)

SHA = "a" * 40
OTHER = "b" * 40


def pr(sha=SHA, repo="quay/quay", state="open", base="master", number=1):
    return {
        "number": number,
        "state": state,
        "base": {"ref": base},
        "head": {"sha": sha, "repo": {"full_name": repo} if repo else None},
    }


def test_select_pr_same_repo_and_fork():
    same, fork = pr(), pr(repo="someone/quay")
    assert pac.select_pr([same], SHA, "quay/quay", ["master"]) is same
    assert pac.select_pr([same, fork], SHA, "someone/quay", ["master"]) is fork


def test_select_pr_rejects_sha_repo_or_base_mismatch():
    assert pac.select_pr([pr(sha=OTHER)], SHA, "quay/quay", ["master"]) is None
    assert pac.select_pr([pr(repo="someone/quay")], SHA, "quay/quay", ["master"]) is None
    assert pac.select_pr([pr(repo=None)], SHA, "quay/quay", ["master"]) is None
    assert pac.select_pr([pr(base="redhat-3.18")], SHA, "quay/quay", ["master"]) is None


def test_eligibility():
    assert pac.ineligible_reason(pr(), SHA, ["master"]) is None
    assert "closed" in pac.ineligible_reason(pr(state="closed"), SHA, ["master"])
    assert "not enrolled" in pac.ineligible_reason(pr(base="redhat-3.18"), SHA, ["master"])
    assert "moved" in pac.ineligible_reason(pr(sha=OTHER), SHA, ["master"])


def test_relevance():
    assert pac.is_relevant(["README.md", "requirements.txt"])
    assert pac.is_relevant(["pyproject.toml"])
    assert pac.is_relevant(["requirements-build.txt"])
    assert pac.is_relevant(["constraints.txt"])
    assert not pac.is_relevant(["requirements-dev.txt", "web/package.json", "sub/requirements.txt"])
    assert not pac.is_relevant([])


def test_already_commented():
    mine = {
        "user": {"login": "github-actions[bot]"},
        "body": "/pipeline remaining\n" + pac.marker(SHA),
    }
    human = {"user": {"login": "someone"}, "body": pac.marker(SHA)}
    assert pac.already_commented([mine], SHA)
    assert not pac.already_commented([mine], OTHER)
    assert not pac.already_commented([human], SHA)


def status(state, context="ci/prow/gcp-gcs"):
    return {"context": context, "state": state, "target_url": "https://prow/run"}


def outcome(statuses, current=None, timed_out=False):
    return pac.poll_outcome(current or pr(), SHA, statuses, "ci/prow/gcp-gcs", timed_out)


def test_poll_outcome_mapping():
    assert outcome([status("success")])[0] == "success"
    assert outcome([status("failure")]) == (
        "failure",
        "ci/prow/gcp-gcs reported failure: https://prow/run. " + pac.RERUN_HINT,
    )
    assert outcome([status("error")])[0] == "failure"
    assert outcome([status("pending")]) is None
    assert outcome([status("success", context="ci/prow/images")]) is None


def test_poll_outcome_timeout():
    conclusion, summary = outcome([status("pending")], timed_out=True)
    assert conclusion == "failure" and "No ci/prow/gcp-gcs result" in summary
    assert outcome([], timed_out=True)[0] == "failure"


def test_poll_outcome_moved_or_closed_cancels():
    assert outcome([status("success")], current=pr(sha=OTHER))[0] == "cancelled"
    assert outcome([], current=pr(state="closed"))[0] == "cancelled"


class FakeGitHub:
    """Stands in for GitHub.request; responses maps (method, path prefix) to a value or callable."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        for (m, prefix), value in self.responses.items():
            if m == method and path.startswith(prefix):
                return value(path) if callable(value) else value
        raise AssertionError(f"unexpected {method} {path}")

    def posts(self, path):
        return [body for m, p, body in self.calls if m == "POST" and p == path]


def stub(monkeypatch, responses):
    fake = FakeGitHub(responses)
    monkeypatch.setattr(pac.GitHub, "request", fake)
    monkeypatch.setattr(pac.time, "sleep", lambda _: None)
    for key, value in {
        "GITHUB_REPOSITORY": "quay/quay",
        "GH_TOKEN": "t",
        "HEAD_SHA": SHA,
        "HEAD_BRANCH": "bump",
        "HEAD_OWNER": "quay",
        "HEAD_REPO": "quay/quay",
    }.items():
        monkeypatch.setenv(key, value)
    return fake


def responses(pulls=None, files=None, comments=(), current=None, statuses=None):
    statuses = statuses or [status("success")]
    return {
        ("GET", "/pulls?"): pulls or [pr(number=20)],
        ("GET", "/pulls/20/files"): files or [{"filename": "requirements.txt"}],
        ("GET", "/issues/20/comments"): list(comments),
        ("GET", "/pulls/20"): current or pr(number=20),
        ("GET", "/commits/"): statuses if callable(statuses) else {"statuses": statuses},
        ("POST", "/issues/20/comments"): {},
        ("POST", "/check-runs"): {"id": 7},
        ("PATCH", "/check-runs/7"): {},
    }


def test_main_comments_on_enrolled_pr_when_an_unenrolled_one_comes_first(monkeypatch):
    pulls = [pr(base="redhat-3.18", number=10), pr(number=20)]
    fake = stub(monkeypatch, responses(pulls=pulls))
    pac.main()
    assert fake.posts("/issues/20/comments") == [
        {"body": "/pipeline remaining\n" + pac.marker(SHA)}
    ]
    patches = [body for m, _, body in fake.calls if m == "PATCH"]
    assert [p["conclusion"] for p in patches] == ["success"]


def test_main_skips_comment_when_marker_present(monkeypatch):
    comment = {"user": {"login": pac.BOT_LOGIN}, "body": pac.marker(SHA)}
    fake = stub(monkeypatch, responses(comments=[comment]))
    pac.main()
    assert fake.posts("/issues/20/comments") == []
    assert len(fake.posts("/check-runs")) == 1


def test_main_head_moved_before_comment_posts_nothing(monkeypatch):
    fake = stub(monkeypatch, responses(current=pr(sha=OTHER, number=20)))
    pac.main()
    assert [m for m, _, _ in fake.calls if m != "GET"] == []


def test_main_rename_away_from_manifest_waits_for_prow(monkeypatch):
    files = [{"filename": "requirements-old.txt", "previous_filename": "requirements.txt"}]
    fake = stub(monkeypatch, responses(files=files))
    pac.main()
    assert fake.posts("/check-runs")[0]["status"] == "in_progress"


def test_main_retries_transient_poll_error(monkeypatch):
    answers = iter(
        [urllib.error.URLError("reset"), TimeoutError(), {"statuses": [status("success")]}]
    )

    def flaky(_path):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    fake = stub(monkeypatch, responses(statuses=flaky))
    pac.main()
    patches = [body for m, _, body in fake.calls if m == "PATCH"]
    assert [p["conclusion"] for p in patches] == ["success"]


def test_main_poll_failure_concludes_check(monkeypatch):
    def broken(_path):
        raise RuntimeError("boom")

    fake = stub(monkeypatch, responses(statuses=broken))
    with pytest.raises(RuntimeError):
        pac.main()
    patches = [body for m, _, body in fake.calls if m == "PATCH"]
    assert [p["conclusion"] for p in patches] == ["failure"]


def test_main_poll_error_past_deadline_concludes_check(monkeypatch):
    errors = iter([TimeoutError(), AssertionError("retried past the deadline")])

    def timeout(_path):
        raise next(errors)

    fake = stub(monkeypatch, responses(statuses=timeout))
    monkeypatch.setattr(pac, "TIMEOUT_MINUTES", 0)
    with pytest.raises(TimeoutError):
        pac.main()
    patches = [body for m, _, body in fake.calls if m == "PATCH"]
    assert [p["conclusion"] for p in patches] == ["failure"]
