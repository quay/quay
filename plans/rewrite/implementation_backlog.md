# Comprehensive Implementation Backlog

Status: Active
Last updated: 2026-02-09

## 1. Operating rules

- Use `plans/rewrite/generated/route_migration_tracker.csv` as the source of truth for endpoint completion.
- Use `plans/rewrite/generated/worker_migration_tracker.csv` as the source of truth for process completion.
- Use `plans/rewrite/program_gates.md` for milestone-level readiness reporting.
- Use `plans/rewrite/signoff_workflow.md` for status promotion and owner signoff rules.
- Use `plans/rewrite/implementation_kickoff_checklist.md` to drive sprint-0 setup.
- No capability is complete until parity tests, canary, and rollback drill pass.

## 2. Workstreams

### WS0: Program control and evidence

Deliverables:
- Capability-level evidence packets (tests, canary, rollback, perf budgets).
- Gate dashboard updates and release go/no-go records.
- Baseline performance capture records for `PB-*` budgets.
- Agent-ready task packets per `ai_agent_guide.md`.

Done when:
- Every capability in trackers has evidence links and budget status.

### WS1: Contract fixtures and test harness

Inputs:
- `plans/rewrite/generated/route_contract_tests.csv`
- `plans/rewrite/generated/queue_worker_contract_tests.csv`
- `plans/rewrite/generated/worker_process_contract_tests.csv`
- `plans/rewrite/test_implementation_plan.md`
- `plans/rewrite/go_module_strategy.md`

Deliverables:
- Runnable route/queue/worker/runtime contract suites.
- Python-oracle vs Go-target comparison harness.
- Traceability fields (`test_file`, `last_run_commit`, `last_passed_at`, `owner`).

Done when:
- Every tracker row maps to a runnable contract test.

### WS2: Ownership switch control plane

Inputs:
- `plans/rewrite/switch_spec.md`
- `plans/rewrite/switch_transport_design.md`
- `plans/rewrite/cutover_matrix.md`

Deliverables:
- Route owner resolution with precedence.
- Worker owner resolution with `python|go|off`.
- Emergency `MIGRATION_FORCE_PYTHON` behavior.

Done when:
- Staging proves owner flips and rollback without deploy.

### WS3: Registry migration (`/v2` then `/v1`)

Inputs:
- `plans/rewrite/registryd_design.md`
- `plans/rewrite/fips_crypto_migration.md`
- `plans/rewrite/storage_backend_inventory.md`

Scope:
- all `registry-v2` rows (19)
- all `registry-v1` rows (26)

Deliverables:
- `registryd` pull/push/manifest/blob/auth parity.
- schema1 signing compatibility.
- chunked upload continuation compatibility across runtimes.
- explicit upload hasher-state compatibility strategy (runtime pinning and shared-format migration path).

Done when:
- Registry route tracker rows are owner=`go` with passing parity/perf/security gates.

### WS4: API and blueprint endpoint migration

Scope:
- `api-v1` routes (268)
- blueprint and app-level non-registry routes (`web`, `oauth*`, `webhooks`, `keys`, `secscan`, `realtime`, `well-known`, `other`)

Deliverables:
- `api-service` parity for all non-registry endpoints.
- parser-gap route canonicalization and fixture coverage.
- route auth checklist completion for migrated waves.

Done when:
- All non-registry tracker rows are owner=`go` and verified.

### WS5: Worker and build-manager migration

Inputs:
- `plans/rewrite/workers_inventory.md`
- `plans/rewrite/notification_driver_inventory.md`

Deliverables:
- Go implementations for each worker pipeline.
- ordered build queue semantics parity.
- notification delivery/event parity.

Done when:
- Worker tracker rows are owner=`go` or explicitly retired by approved decision.

### WS6: Queue engine and payload compatibility

Inputs:
- `plans/rewrite/queue_contracts.md`
- `plans/rewrite/queue_cutover_dependencies.md`

Deliverables:
- mixed producer/consumer compatibility for all nine queues.
- lease/retry/ordering semantics parity.
- verified route-to-producer call-path evidence for indirect producers.

Done when:
- Queue contract and replay tests pass in mixed mode and go-only mode.

### WS7: Auth and identity parity

Inputs:
- `plans/rewrite/auth_backend_inventory.md`

Deliverables:
- auth mode parity + backend/provider parity.
- provider conformance tests (DB, LDAP, JWT, Keystone, AppToken, OIDC).
- federated identity and team sync parity.

Done when:
- No auth/provider regressions in canary and signoff rows are verified.

### WS8: Data layer and schema evolution

Inputs:
- `plans/rewrite/db_migration_policy.md`
- `plans/rewrite/data_access_layer_design.md`

Deliverables:
- Go DAL implementation with pooling, retry, and replica routing parity.
- encrypted-field compatibility validation.
- expand->migrate->contract evidence for schema-affecting changes.
- queue optimistic concurrency parity (`state_id` regeneration + CAS behavior).
- credential hashing parity (bcrypt) and delete-semantics parity hooks.

Done when:
- Mixed Python/Go runtime passes DB consistency and rollback checks.

### WS9: Platform security, TLS, and FIPS

Inputs:
- `plans/rewrite/fips_crypto_migration.md`
- `plans/rewrite/tls_security_posture.md`

Deliverables:
- FIPS crypto wrappers and compatibility fixtures.
- TLS termination and cipher policy migration plan execution.
- security regression gates integrated into cutover checklist.
- inventory coverage for registry JWT/OIDC JWT/secscan JWT/PKCE/Swift/CDN signing primitives.

Done when:
- Security/TLS/FIPS checks pass for all migrated capabilities.

### WS10: Runtime support components and Redis patterns

Inputs:
- `plans/rewrite/runtime_support_components.md`
- `plans/rewrite/runtime_component_execution_plan.md`
- `plans/rewrite/redis_usage_inventory.md`

Deliverables:
- runtime support component parity or approved retirement.
- Redis pattern parity (Lua, locks, pub/sub, orchestrator semantics).

Done when:
- Runtime mapping rows are completed or retired-approved with evidence.

### WS11: Deployment and image modernization

Inputs:
- `plans/rewrite/deployment_architecture.md`
- `plans/rewrite/config_tool_evolution.md`
- `plans/rewrite/image_strategy.md`

Deliverables:
- K8s and VM deployment references for Go services.
- config-tool schema updates for rewrite switch/runtime keys.
- milestone image BOM and component elimination execution.
- multi-arch and FIPS build matrix validation.

Done when:
- Canary environments run on planned deployment/image model.

### WS12: Route auth verification acceleration

Inputs:
- `plans/rewrite/route_auth_automation_plan.md`
- `plans/rewrite/scripts/route_auth_auto_verify.py`

Deliverables:
- automated route auth pre-verification report.
- manual backlog reduced to targeted exception set.
- remaining rows assigned and closed via signoff waves.

Done when:
- `source-anchored-needs-review` rows are <= 50 before broad implementation starts.

## 3. Decision baseline

Canonical register:
- `plans/rewrite/open_decisions.md`

Current status:
- D-005 approved: repo mirror migration uses Go-native `containers/image`.

## 4. Completion definition

Migration planning is complete when:
- every route/process/queue/runtime-component row is represented in a workstream with explicit test IDs,
- missing architecture artifacts (G8-G15) are approved,
- switch and rollback designs are concrete,
- and no unresolved high-risk inventory gaps remain.
