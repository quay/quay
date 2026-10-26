# Collector output: full field reference

`scripts/playwright-debug-prow.sh` prints one JSON object on success (exit 0)
or on "still in progress" (exit 2, a smaller object with `build_id`,
`prow_url`, `status`, `error`). This is the full shape of the success object,
grouped by purpose. Every field name below is taken directly from the
collector's final `jq` filter.

## Identity and links

- `build_id`, `job_name`, `prow_url`, `gcsweb_url`, `job_status` — which run
  this is and where to view it.
- `artifacts_dir` — the collector's scratch directory, under the repo's
  `tmp/`. Removed by the collector itself on any nonzero exit; left in place
  on success for the caller to read from and then remove.
- `artifact_base_url` — the GCS URL prefix the e2e step's own artifacts
  (`results.json`, JUnit, attachments, `data/`, `builder-diagnostics/`) were
  found under.
- `html_report_url` — the HTML report's GCSWeb URL, or empty if it was never
  produced or was itself the CI redaction placeholder (a HEAD request alone
  cannot tell a real report from the placeholder; the collector reads its
  first 256 bytes to check).

## Routing records

Each of these is a `{source_url, local_path, status}` object;
`status` is `"downloaded"` or `"unavailable"`, and `local_path` is `null`
when unavailable. They exist so a triager never has to refetch the objects
that identify the run and its steps:

- `prowjob` — `prowjob.json`, the Prow CRD: run identity and overall
  `status.state`. Always downloaded (the collector uses it to decide whether
  the job has completed before doing anything else).
- `clone_records` — `clone-records.json`, ci-operator's log of the sparse
  source clone(s) it performed. Feeds `provenance.source_clone_sha` and
  `provenance.source_clone_ref`.
- `finished` — `finished.json`, the build-root Prow job's overall result
  (**not** the e2e step's own result). Feeds `provenance.job_result`, and is
  a fallback source for `provenance.source_clone_ref` when `clone_records`
  has no usable `refs.base_ref`.
- `top_level_build_log` — the run's top-level `build-log.txt` (the whole
  ci-operator step sequence), distinct from `step_build_log` below.
- `step_build_log` — the e2e step's own `build-log.txt`, fetched from the
  e2e step's artifact root. This is the file `has_build_log` /
  `Step 3b: Correlate with build log` refer to. Also the source
  `provenance.playwright_sha` is parsed from.
- `junit` — an **array** of `{source_url, local_path, status}`, one per
  JUnit XML file discovered directly alongside `results.json` (normally one,
  `junit_playwright.xml`; a sharded run can have several). Discovered by
  listing the artifact prefix and filtering on `*junit*.xml`, not by probing
  one fixed name.

## Provenance

`provenance` holds ten `{value, reason}` pairs. `reason` is always set when
`value` is null, naming which upstream field was absent — treat a null
`value` as an evidence gap, never as "no data to report". A few fields also
set `reason` alongside a non-null `value` to explain how that value was
derived (see `auth_mode` and `actual_workers` below):

- `source_image_digest`, `release_config_revision` — build-level identifiers;
  `reason` explains why the collector could not resolve them for this run.
- `auth_mode` — always `"anonymous"` with a fixed reason: the collector never
  sends credentials, so this is a fact about the collector's own requests,
  not something read out of a downloaded artifact.
- `actual_workers` — from `config.projects[].metadata.actualWorkers` in
  `results.json`, falling back to the root `config.workers` value when no
  project reports `actualWorkers`. When the fallback fires, `value` is the
  root `config.workers` figure and `reason` names the fallback; when both
  sources are absent, `value` is null and `reason` names both fields.
- `retries` — the max `config.projects[].retries` across projects.
- `tracing_configuration` — `config.projects[].use.trace` when serialized, or
  (when absent) an inferred description built from the count of `trace`
  attachments actually present in `results.json`.
- `source_clone_sha`, `source_clone_ref` — from `clone_records` (with the
  `finished.revision` fallback described above).
- `playwright_sha` — parsed from a `PLAYWRIGHT_SOURCE_PROVENANCE` line in the
  step build log (`repo=... ref=... sha=...`); `reason` distinguishes a step
  that predates this line, a line that failed to parse, and a step that
  printed `sha=unknown` (archive fallback, no git metadata).
- `job_result` — from `finished.result`.

## Per-attachment validation

Every attachment Playwright advertises (screenshot, video, trace) on any
`attempts[]` entry anywhere in `results.json` — passed attempts included, not
just `failed`/`flaky` tests — is downloaded once and classified:

- `usable` — downloaded and, for a trace zip, passed both a magic-byte check
  and `unzip -t`.
- `redacted` — the CI sensitive-content placeholder (the same text checked
  for redacted pod logs) was found in the downloaded content.
- `missing` — download failed, the object was capped out (more than 100
  discovered attachments in one run), or a trace zip failed its integrity
  check (bad magic bytes, corrupt archive, or `unzip` unavailable to check
  with).
- `inline` — the attachment has no `path` in `results.json` (nothing to
  download) but does have a `body`, so the content is already embedded in
  `results.json`. `url` is `null` and the body itself is not emitted.

`reason` is set on every non-`usable` status and is `null` on `usable`.

## Evidence gaps

`evidence_gaps` is **run-level**, not per-attachment: it covers artifacts a
missing entry would otherwise look like silently absent evidence rather than
a recorded gap.

- `must-gather.tar`, at the workflow's `gather-must-gather/artifacts/`
  prefix: a `{artifact: "must-gather.tar", source_url, status, reason}`
  record appears only when the object came back `redacted`, or `missing`
  because a HEAD probe or a range read failed (`reason` distinguishes the
  two). A job whose `gather-must-gather` step never ran (a HEAD 404) produces
  no record at all — that is not a gap.
- HTML report `data/` blobs, at `artifact_base_url/data/`: each redacted or
  missing (or unprobeable) blob gets its own
  `{artifact, source_url, status, reason}` record, `artifact` prefixed
  `data/`.

## Builder diagnostics

`builder_diagnostics` lists every file found under the e2e step's
`builder-diagnostics/` prefix (up to 100), each downloaded and previewed:

```json
{"name": "...", "source_url": "...", "local_path": "...", "status": "downloaded", "first_lines": ["..."]}
```

`first_lines` is at most 40 ANSI-stripped lines, each truncated to 500
characters — a preview, never the whole file. A key whose name is not a
flat, single-component filename is reported with `status: "unavailable"` and
an empty `first_lines` rather than written to disk. An absent prefix (nothing
found) produces `[]`, not a gap record.

## Container logs and Jaeger

- `has_container_logs`, `container_log_files`, `redacted_container_log_files`
  — Quay pod logs discovered under the workflow's `gather-extra/artifacts/pods/`
  prefix, matched on `*_quay-app.log`. Usable files are concatenated to
  `$ARTIFACTS_DIR/container-logs/quay.log`; empty logs are ignored, and
  redacted filenames are reported separately rather than treated as usable.
- `has_jaeger_traces`, `jaeger_trace_files`, `jaeger_artifact_base_url` —
  legacy `traces.json` and chunked `traces-*.json` files discovered under the
  workflow's `quay-gather-jaeger-traces` prefix, downloaded under
  `$ARTIFACTS_DIR/jaeger-traces/` only after JSON validation.

## Test outcome arrays and stats

- `stats` — `total`, `passed`, `failed`, `flaky`, `skipped`, `duration_s`,
  `start_time`.
- `failed[]` — `title`, `file`, `line`, `project`, `error_message`
  (ANSI-stripped, from the last attempt), `attempts[]` (`retry`, `status`,
  `duration`, `errors[]`, `attachments[]`).
- `flaky[]` — same per-attempt shape, plus `retries` (max retry count) and
  `first_error` (from the first attempt).
- `skipped[]` — `title`, `file`, `line`, `reason` (the skip annotation).
- `interrupted[]` — `title`, `file`, `line`, `project`, for any test with an
  `interrupted` result on any attempt.
- `global_setup_failure` — `true` when the run's total test count is zero.
- `setup_errors[]` — top-level `results.json` `.errors[]` messages
  (ANSI-stripped); the detail to read when `global_setup_failure` is true.
