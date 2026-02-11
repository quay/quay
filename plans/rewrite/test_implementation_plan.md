# Contract Test Implementation Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Define how generated test IDs become runnable parity tests and CI gates for Python-oracle vs Go-target execution.

## 2. Test suites to implement

1. Route contract suite
- Source IDs: `route_contract_tests.csv`
- Test namespace: `tests/rewrite/contracts/routes/`
- Naming: `<parity_test_id>_test.go`

2. Queue contract suite
- Source IDs: `queue_worker_contract_tests.csv`
- Test namespace: `tests/rewrite/contracts/queues/`
- Naming: `<consumer_behavior_test_id>_test.go`

3. Worker process behavior suite
- Source IDs: `worker_process_contract_tests.csv`, `worker_verification_checklist.csv`
- Test namespace: `tests/rewrite/contracts/workers/`
- Naming: `<behavior_test_id>_test.go`

4. Runtime support suite
- Source IDs: `runtime_component_mapping.csv`
- Test namespace: `tests/rewrite/contracts/runtime/`
- Naming: `<parity_test_id>_test.go`

## 3. Harness model

- Contract tests are HTTP/event-level and language-agnostic.
- Run each test against two targets:
- Python oracle target (`REWRITE_TARGET=python`)
- Go candidate target (`REWRITE_TARGET=go`)
- Compare status, headers, body schema, side effects, and metrics deltas.

## 4. CI gating plan

1. Stage 1: non-blocking nightly parity runs.
2. Stage 2: blocking on touched capability families.
3. Stage 3: blocking global parity + performance-budget gate for owner flips.

## 5. Artifact-to-test traceability

Each generated row must have:
- `test_file`
- `last_run_commit`
- `last_passed_at`
- `owner`

Store traceability in CSV manifests under `plans/rewrite/generated/`.
