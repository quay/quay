# Performance Budget and Baseline Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Define measurable latency, throughput, and reliability budgets that gate capability ownership flips.

## 2. Baseline collection policy (M0 requirement)

- Collect Python baseline for 14 consecutive days on representative workloads.
- Capture P50/P95/P99, error rate, saturation signals, and queue lag.
- Record baseline snapshots in versioned artifacts under `plans/rewrite/generated/`.
- Track active collection progress in `plans/rewrite/generated/performance_baseline_status.md`.

## 3. Budget IDs and thresholds

| Budget ID | Surface | Threshold |
|---|---|---|
| `PB-REG-AUTH` | Registry auth/token exchange | P95 <= baseline + 10%, P99 <= baseline + 15% |
| `PB-REG-PULL` | Registry pull hot paths | P95 <= baseline + 10%, error rate not worse than baseline + 0.2% |
| `PB-REG-PUSH` | Registry push/upload finalize | P95 <= baseline + 15%, no digest mismatch regression |
| `PB-API-HOT` | `/api/v1` hot endpoints | P95 <= baseline + 10% |
| `PB-WORKER-LAG` | Queue lag and worker throughput | queue lag P95 <= baseline + 15% |
| `PB-DB-SAFETY` | DB query latency on large datasets | no new full scans on critical paths; P99 <= baseline + 15% |

## 4. Large-DB safety rules

1. Require query-plan review for changed high-cardinality queries.
2. Add regression checks for N+1 query patterns.
3. Require index-impact review for any new filter/sort paths.

## 5. Measurement cadence

- Pre-cutover: full budget run for impacted capability family.
- Canary: 1h, 6h, and 24h budget checks.
- Post-cutover: daily checks during rollback window.

## 6. Failure policy

- Any threshold breach blocks owner flip completion.
- Severe regression triggers immediate rollback per `switch_spec.md`.
- Exception requires explicit approval and expiry date.
