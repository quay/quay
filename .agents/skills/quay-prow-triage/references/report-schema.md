# Quay Prow triage report schema

Fill in every field below in the report, every run, whether the diagnosis is
confident or not.

## Outcome and cause fields

- **`tests_executed`**: counts of passed, failed, recovered, skipped,
  interrupted and not-run. Preserve all failed attempts even on a green job.
- **Failure category**: one of `product`, `test` (selector/isolation/timing),
  `auth-config`, `ci-pipeline`, `cluster-cloud`, `unknown`, plus a subtype and
  the implicated component.
- **Normalized signature**, per failure, for grouping matching failures from
  different runs onto one cause.
- **Root-cause claim**, or `unknown`.
- **Confidence**, recorded separately from collection state:
  - `high` — originating error plus matching evidence.
  - `medium` — supported failure class, deeper cause unproved.
  - `low` — symptom or hypothesis only.

## Evidence fields

- **Collection state**: `complete`, `partial`, or `unavailable`, each with a
  reason.
- **Evidence list**: one row per item, each with a provenance URL or
  `file:line`.
- **Evidence gaps**: every 403, missing field, or absent artifact, listed
  explicitly (see section d's addition for the `triage-flaky-test`
  access-gap case).
- **Alternatives rejected**, and why — an empty list means untested, not
  ruled out.

## Output fields

- **Proposed fix**, with an owner and a verification command. This
  authorizes nothing; it is a suggestion for whoever acts on the report.
- **Draft Jira text** and **draft quarantine proposal** — only when
  warranted, and marked as drafts that authorize nothing on their own.

## Retry handling

State plainly, every time retries are involved: retry recovery is an
outcome, never a cause and never proof of harmlessness. A timeout alone
proves no cause either.
