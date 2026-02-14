# Rewrite Decision Log

Status: Active
Last updated: 2026-02-09

## 1. Purpose

Record approvals and final outcomes for open rewrite decisions.

## 2. Decision records

| Decision ID | Outcome | Approved by | Approval date | Effective date | Notes |
|---|---|---|---|---|---|
| `D-001` | approved | user | 2026-02-08 | 2026-02-08 | approved removal of stale `ip-resolver-update-worker` references |
| `D-002` | approved | user | 2026-02-08 | 2026-02-08 | approved Option B switch transport |
| `D-003` | approved | user | 2026-02-08 | 2026-02-08 | approved DB exception governance recommendation |
| `D-004` | approved | user | 2026-02-08 | 2026-02-08 | operational CLI scripts not critical; no Go migration required (default `retire-approved`) |
| `D-005` | approved | user | 2026-02-09 | 2026-02-09 | approved migration to Go-native `containers/image` for repo mirror path |

## 3. Pending decisions (not yet approved)

| Decision ID | Current status | Notes |
|---|---|---|
| `none` | n/a | all current listed decisions are approved |

## 4. Requirements

- Every approved decision must be reflected in:
  - `plans/rewrite/open_decisions.md` (status update)
  - impacted sub-plan(s)
