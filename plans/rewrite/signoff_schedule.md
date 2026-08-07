# Rewrite Signoff Schedule

Status: Proposed
Last updated: 2026-02-09

## 1. Purpose

Provide a concrete review cadence for checklist promotion from source-anchored to verified.

## 2. Weekly schedule proposal

| Week (start) | Route waves | Worker waves | Runtime waves | Primary goals |
|---|---|---|---|---|
| 2026-02-09 | `A1`..`A4` owner-signoff promotion | `P0`, `P1` (+ retired-decision review) | `W1` | Convert route rows from `verified-source-anchored` to `verified` with owner evidence; verify rollback drills |
| 2026-02-16 | route cleanup pass | `P2` | `W2` | Complete queue-coupled worker signoff and dependent route evidence |
| 2026-02-23 | route cleanup pass | `P3`, `P4` | `W2` | Close remaining owner-signoff gaps and GC-coupled dependencies |
| 2026-03-02 | final route verification audit | `P5` | `W3` | Finalize builder/runtime signoff and unresolved regressions |

## 3. Session checklist per weekly review

1. Review prior-week regressions and rollback drills.
2. Verify test evidence links for target batches.
3. Confirm owner signoff in checklist rows.
4. Promote eligible rows to `verified`.
5. Update `program_gates.md` and `rewrite_snapshot.md`.

## 4. Dependency cautions

- `A3` secscan routes and `P2` secscan workers should be reviewed together.
- `A2` slices that trigger queue-producing model paths must respect `queue_cutover_dependencies.md`.
- `P0` retired-decision row (`PROC-008`) is historical evidence, not active verification work.
