# Operational Tooling Migration Plan

Status: Active (D-004 baseline approved)
Last updated: 2026-02-09

## 1. Purpose

Cover Python operational/admin scripts so migration scope includes runtime tooling, not only HTTP endpoints and workers.

## 2. Inventory source

- `plans/rewrite/generated/operational_tooling_inventory.md`
- `plans/rewrite/generated/operational_tooling_disposition.csv`
- `plans/rewrite/generated/operational_tooling_disposition_summary.md`

## 2.1 Approved decision baseline

Per D-004 approval (2026-02-08):
- Operational CLI scripts are not considered critical to the Go migration target.
- Default disposition is `retire-approved`.
- Go migration is not required unless a future exception is explicitly approved.

## 3. Policy

Supported dispositions:

1. `go-port-required`
- Script supports production operations or SRE/admin runbooks and must remain available.

2. `retire-approved`
- Script is obsolete and can be removed with documented replacement/no-op guidance.

3. `python-compat-window`
- Script remains Python-only temporarily during transition with explicit sunset date.

## 4. Execution checklist per script

1. Identify users/runbooks that depend on the script.
2. Document input/output contract and side effects.
3. Assign disposition (`retire-approved` by default per D-004).
4. If porting, define Go command path and compatibility tests.
5. If retiring, add approval note and fallback runbook.
6. Record status in implementation backlog evidence.

## 5. Priority buckets

- `P-ops-high`: credential/key generation, replication/data-migration admin tasks.
- `P-ops-medium`: invoicing/email/manual support scripts.
- `P-ops-low`: one-off diagnostics with no production dependency.

## 6. Completion criteria

- Every inventory row has an approved disposition.
- No production runbook references an unmapped Python-only script.

## 7. Transition safety check

- Before declaring tooling scope closed, run a transition-period check:
  - identify scripts used only during migration (cutover, rollback, emergency diagnostics)
  - reclassify any such script from `retire-approved` to `python-compat-window` or `go-port-required`
- Track temporary compatibility scripts with explicit sunset dates.
