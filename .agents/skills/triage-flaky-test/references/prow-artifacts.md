# Stage B detail: locating and reading Prow artifacts

### B1: the object path is derived from the job name and the build id

Nothing else is needed to reach the artifacts — no Prow URL, no browser:

| Job kind | Object prefix |
|---|---|
| periodic | `logs/<job-name>/<build-id>/artifacts/...` |
| presubmit | `pr-logs/pull/<org>_<repo>/<pr-number>/<job-name>/<build-id>/artifacts/...` |

The presubmit shape is `quay_quay` with an underscore, PR number before the job
name — e.g. `pr-logs/pull/quay_quay/7148/pull-ci-quay-quay-master-images/2100325289690140672/`.

### B2: new runs — `test-platform-results-public`, anonymous, no auth

Runs that landed **after** the bucket rename are world-readable in
`test-platform-results-public`. This is the default path; try it first.

```bash
BUCKET=test-platform-results-public
JOB=periodic-ci-quay-quay-redhat-3.18-gcp-ocp422-e2e-install-gcp-gcs-nightly

# build ids for a job; latest-build.txt holds the newest
curl -sS "https://storage.googleapis.com/storage/v1/b/$BUCKET/o?prefix=logs%2F$JOB%2F&delimiter=%2F&maxResults=100" | jq -r '.prefixes[]?'
curl -sS "https://storage.googleapis.com/$BUCKET/logs/$JOB/latest-build.txt"

# what the Playwright step of one run holds
BUILD=2100145201472344064
S=logs/$JOB/$BUILD/artifacts/gcp-gcs-nightly/quay-test-e2e
curl -sS "https://storage.googleapis.com/storage/v1/b/$BUCKET/o?prefix=$(jq -rn --arg s "$S/" '$s|@uri')&maxResults=1000" | jq -r '.items[]?.name'

# fetch one object: the XML API takes the path verbatim, no percent-encoding
curl -sS -o results.json "https://storage.googleapis.com/$BUCKET/$S/artifacts/results.json"
```

gcloud reaches the same objects anonymously once credentials are switched off:

```bash
CLOUDSDK_AUTH_DISABLE_CREDENTIALS=1 gcloud storage ls "gs://$BUCKET/logs/$JOB/"
CLOUDSDK_AUTH_DISABLE_CREDENTIALS=1 gcloud storage cp "gs://$BUCKET/$S/artifacts/results.json" .
```

The directory under `artifacts/<variant>/` is the ci-operator step name —
`quay-test-e2e` for the quay nightlies. Its own `artifacts/` holds
`results.json` (JSON reporter), `junit_playwright.xml`, `index.html` (HTML
report), `playwright-output.log`, and one directory per failed test with
`test-failed-1.png` and `trace.zip` — trace is `retain-on-failure`, so every
failed attempt keeps its own trace, including the first before any retry.
`results.json` is still the primary evidence for the failure itself: it
carries the error message, `workerIndex`, `parallelIndex` and `startTime` for
every attempt.

List the step prefix, not the run: a whole-run listing paginates (an install
job run holds well over 2000 objects and the response carries a
`nextPageToken`), while the step prefix fits in one call.

### B3: old runs — `test-platform-results`, needs auth, fallback only

Runs from **before** the rename stay in the private `test-platform-results`
bucket: anonymous calls get **401** from the JSON API and **403** on an object,
and the collector fails the same way. The authenticated path is the same prefix:

```bash
gcloud auth login                       # interactive; do not attempt from an agent session
gcloud storage ls gs://test-platform-results/logs/<job-name>/<build-id>/
```

`gcloud auth login` is interactive and cannot be run from this session. Report
the access gap to the caller — which bucket and prefix were tried, and that
authenticated access was not attempted — and fall back to Stage A plus Stage C.

### B4: substituting the bucket by hand

The collector takes the bucket from the URL and fetches anonymously, so it
works on post-rename runs as-is — but only if the URL names the public
bucket. Substitute it by hand if the URL you were handed still says
`test-platform-results`:

```
.../view/gs/test-platform-results-public/logs/<job-name>/<build-id>
```
