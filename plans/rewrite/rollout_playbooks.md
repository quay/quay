# Rewrite Rollout Playbooks

Status: Draft
Last updated: 2026-02-08

## 1. Goal

Standardize safe rollout, canary, and rollback for every capability.

## 2. Generic playbook per capability

1. Preconditions
- Go implementation deployed but disabled.
- Contract tests green for capability.
- Observability dashboards and alerts ready.
- Rollback switch verified in staging.
- Owner switches conform to `plans/rewrite/switch_spec.md`.

2. Canary
- Enable Go owner for a narrow cohort (org/repo/tenant).
- Run synthetic checks and shadow comparisons.
- Hold for defined burn-in window.

3. Expansion
- Increase cohort gradually.
- Track error budget, latency, queue lag, and correctness deltas.
- Pause or rollback immediately on threshold breach.

4. Completion
- Set owner=`go` globally.
- Disable Python owner path/process.
- Archive migration evidence and rollback notes.

## 3. Registry playbook notes

- Separate pull, push, auth, and manifest/blob capabilities where practical.
- Keep `/v1/*` and `/v2/*` on independent owner switches.
- Reference ordering: `plans/rewrite/generated/route_family_cutover_sequence.md`.

## 4. Worker playbook notes

- Run producer/consumer mixed-mode tests first.
- Enable Go consumers while Python producers remain active.
- Disable Python consumers via supervisor/feature controls only after stability.
- Reference ordering: `plans/rewrite/generated/worker_phase_sequence.md`.

## 5. Rollback triggers

- Contract mismatch detected.
- Elevated error rate beyond threshold.
- Latency/SLO breach.
- Queue backlog growth beyond threshold.
- Data integrity invariant failure.

## 6. Rollback actions

- Flip capability owner back to `python`.
- Re-enable Python worker/program where applicable.
- Keep Go component deployed but disabled for forensics.
- Run post-rollback consistency checks and incident notes.
