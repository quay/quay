# Rewrite Decision Log

Status: Active
Last updated: 2026-02-12

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
| `D-006` | open | Go HTTP router choice: `chi/v5` vs `net/http` (stdlib). Recommendation: `net/http` with thin internal helpers. Blocks WS3/WS4 handler registration. |
| `D-007` | open | Coexistence deployment topology: where does Go binary run during M1-M4? Recommendation: hybrid (same container for standalone, separate Deployments for K8s). Blocks M1, WS2, WS11. |
| `D-008` | open | Upload hasher state cross-runtime strategy. Recommendation: capability-level read/write split (pull→Go, push→Python) instead of UUID pinning or shared hasher format. Eliminates cross-runtime serialization problem entirely. Blocks WS3. |

## 4. Requirements

- Every approved decision must be reflected in:
  - `plans/rewrite/open_decisions.md` (status update)
  - impacted sub-plan(s)
