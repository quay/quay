# Verification and Signoff Workflow

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Standardize how checklist rows move from source-anchored to fully verified.

## 2. Applicable artifacts

- `plans/rewrite/generated/route_auth_verification_checklist.csv`
- `plans/rewrite/generated/worker_verification_checklist.csv`
- `plans/rewrite/generated/runtime_component_mapping.csv`
- `plans/rewrite/generated/route_auth_auto_verification_report.md`
- `plans/rewrite/generated/signoff_batch_review_packet.md`
- `plans/rewrite/generated/owner_assignment_matrix.csv`
- `plans/rewrite/generated/owner_assignment_summary.md`
- `plans/rewrite/signoff_schedule.md`

## 3. Required evidence per row

1. Source evidence
- Existing `*_evidence_ref` field points to file:line anchor(s).

2. Test evidence
- Parity test ID execution result (pass/fail + commit SHA).

3. Owner signoff
- Fill `owner_signoff` with team/user + date.

4. Rollback note
- Confirm rollback behavior for that row/capability.

## 4. Status transition

- `source-anchored-needs-review` -> `verified` when owner confirms source + tests.
- `verified-source-anchored` -> `verified` when owner_signoff and test evidence are complete.
- `needs-triage` -> `retired-approved` or `verified` after decision closure.
- `source-anchored-needs-review` -> `verified-source-anchored` may be set by automation (`route_auth_auto_verify.py`) for high-confidence rows; human owner signoff is still required for `verified`.

## 5. Audit cadence

- Update checklists at least once per milestone review.
- Reflect major status changes in `program_gates.md` and `temp.md`.
- Execute owner signoff in review-batch order from `signoff_batch_review_packet.md`.
- Use weekly cadence proposed in `signoff_schedule.md` unless superseded by release plan.
