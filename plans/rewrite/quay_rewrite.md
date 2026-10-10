# Quay Rewrite Master Plan (Python -> Go)

Status: Active
Last updated: 2026-02-11

## 1. Scope and non-negotiables

This migration rewrites Quay backend components from Python to Go with zero contractual regressions.

Hard requirements:
- Keep all API contracts and externally visible behavior intact.
- Keep `/v1/*` fully supported in the Go target.
- Keep `/v2/*` fully supported in the Go target.
- Migrate all endpoints and all background processes; nothing is out of scope.
- Support graceful incremental cutover:
  - Introduce Go per capability/path.
  - Disable equivalent Python capability after parity/canary validation.
  - Ensure Python + Go together always provide complete service.
- Preserve DB and object storage invariants unless explicitly approved and migration-tested.
- Preserve mirror-registry/disconnected install viability.
- Unify mirror-registry into the Go binary, replacing Ansible/EE orchestration.
- Maintain FIPS-required deployment support.

## 2. Document map (master + sub-plans)

This master is intentionally concise. Detailed plans are split into sub-docs.

- API surface inventory and migration map:
  - `plans/rewrite/api_surface_inventory.md`
- Workers/process inventory and migration map:
  - `plans/rewrite/workers_inventory.md`
- Queue contracts (schema, semantics, payloads):
  - `plans/rewrite/queue_contracts.md`
- Queue-to-route/worker dependency sequencing:
  - `plans/rewrite/queue_cutover_dependencies.md`
- Capability cutover ownership matrix (Python vs Go):
  - `plans/rewrite/cutover_matrix.md`
- Concrete switch and rollback control specification:
  - `plans/rewrite/switch_spec.md`
- Switch transport design (distribution + runtime propagation):
  - `plans/rewrite/switch_transport_design.md`
- Contract and regression testing strategy:
  - `plans/rewrite/test_strategy.md`
- Contract test implementation plan:
  - `plans/rewrite/test_implementation_plan.md`
- Performance budget and baseline plan:
  - `plans/rewrite/performance_budget.md`
- Route auth auto-verification plan:
  - `plans/rewrite/route_auth_automation_plan.md`
- DB/data evolution and compatibility policy:
  - `plans/rewrite/db_migration_policy.md`
- Data access layer migration architecture:
  - `plans/rewrite/data_access_layer_design.md`
- Go module and CI bootstrap strategy:
  - `plans/rewrite/go_module_strategy.md`
- FIPS and crypto migration plan:
  - `plans/rewrite/fips_crypto_migration.md`
- Storage backend inventory and migration tracker:
  - `plans/rewrite/storage_backend_inventory.md`
  - `plans/rewrite/generated/storage_driver_migration_tracker.csv`
- Registry implementation architecture:
  - `plans/rewrite/registryd_design.md`
- Redis usage inventory:
  - `plans/rewrite/redis_usage_inventory.md`
- Runtime support components inventory:
  - `plans/rewrite/runtime_support_components.md`
- Runtime support component execution sequencing:
  - `plans/rewrite/runtime_component_execution_plan.md`
- Operational/admin tooling migration:
  - `plans/rewrite/operational_tooling_plan.md`
- Deployment architecture (Kubernetes + VM):
  - `plans/rewrite/deployment_architecture.md`
- Config-tool co-evolution plan:
  - `plans/rewrite/config_tool_evolution.md`
- Container image strategy:
  - `plans/rewrite/image_strategy.md`
- TLS/security posture:
  - `plans/rewrite/tls_security_posture.md`
- Auth backend/provider inventory:
  - `plans/rewrite/auth_backend_inventory.md`
- Notification driver inventory:
  - `plans/rewrite/notification_driver_inventory.md`
- Unified CLI and mirror-registry integration:
  - External design: `https://gist.github.com/jbpratt/f23cef1dcabcac3dec55ec55578abd9a`
- Existing Go implementation (prototype) and reconciliation:
  - Source: `https://github.com/quay/quay-distribution`
  - Reconciliation report: `plans/rewrite/quay_distribution_reconciliation.md`
- Architecture diagrams (team review):
  - `plans/rewrite/architecture_diagrams.md`
- AI agent implementation guide:
  - `plans/rewrite/ai_agent_guide.md`
- Rollout and rollback playbooks:
  - `plans/rewrite/rollout_playbooks.md`
- Comprehensive implementation backlog/workstreams:
  - `plans/rewrite/implementation_backlog.md`
- Implementation kickoff checklist:
  - `plans/rewrite/implementation_kickoff_checklist.md`
- Program gate dashboard:
  - `plans/rewrite/program_gates.md`
- Verification/signoff workflow:
  - `plans/rewrite/signoff_workflow.md`
- Verification/signoff schedule:
  - `plans/rewrite/signoff_schedule.md`
- M0 readiness checklist:
  - `plans/rewrite/m0_readiness_checklist.md`
- Pending planning decisions register:
  - `plans/rewrite/open_decisions.md`
- Decision approval log:
  - `plans/rewrite/decision_log.md`
- Decision approval packet:
  - `plans/rewrite/decision_approval_packet.md`
- Specific triage decision package (`ip-resolver-update-worker`):
  - `plans/rewrite/ip_resolver_update_worker_disposition.md`
- Generated exhaustive inventory artifacts:
  - `plans/rewrite/generated/route_inventory.md`
  - `plans/rewrite/generated/non_blueprint_route_inventory.md`
  - `plans/rewrite/generated/route_migration_tracker.csv`
  - `plans/rewrite/generated/route_migration_tracker_summary.md`
  - `plans/rewrite/generated/route_auth_verification.md`
  - `plans/rewrite/generated/route_auth_verification_checklist.csv`
  - `plans/rewrite/generated/route_auth_verification_checklist_summary.md`
  - `plans/rewrite/generated/route_auth_manual_backlog.md`
  - `plans/rewrite/generated/route_auth_review_waves.md`
  - `plans/rewrite/generated/route_auth_auto_verification_report.md`
  - `plans/rewrite/generated/route_parser_gaps.md`
  - `plans/rewrite/generated/route_family_cutover_sequence.md`
  - `plans/rewrite/generated/route_contract_tests.csv`
  - `plans/rewrite/generated/auth_mode_matrix.md`
  - `plans/rewrite/generated/route_family_counts.md`
  - `plans/rewrite/generated/feature_gate_inventory.md`
  - `plans/rewrite/generated/worker_inventory.md`
  - `plans/rewrite/generated/worker_migration_tracker.csv`
  - `plans/rewrite/generated/worker_migration_tracker_summary.md`
  - `plans/rewrite/generated/worker_phase_sequence.md`
  - `plans/rewrite/generated/worker_process_contract_tests.csv`
  - `plans/rewrite/generated/worker_process_contract_tests_summary.md`
  - `plans/rewrite/generated/worker_semantics_verification.md`
  - `plans/rewrite/generated/worker_verification_checklist.csv`
  - `plans/rewrite/generated/worker_verification_checklist_summary.md`
  - `plans/rewrite/generated/worker_verification_progress.md`
  - `plans/rewrite/generated/worker_module_coverage_audit.md`
  - `plans/rewrite/generated/queue_inventory.md`
  - `plans/rewrite/generated/queue_payload_inventory.md`
  - `plans/rewrite/generated/queue_worker_contract_tests.csv`
  - `plans/rewrite/generated/http_surface_coverage_audit.md`
  - `plans/rewrite/generated/worker_process_coverage_audit.md`
  - `plans/rewrite/generated/route_worker_dependency_matrix.csv`
  - `plans/rewrite/generated/route_worker_dependency_matrix.md`
  - `plans/rewrite/generated/runtime_component_mapping.csv`
  - `plans/rewrite/generated/runtime_component_mapping_summary.md`
  - `plans/rewrite/generated/operational_tooling_inventory.md`
  - `plans/rewrite/generated/operational_tooling_disposition.csv`
  - `plans/rewrite/generated/operational_tooling_disposition_summary.md`
  - `plans/rewrite/generated/owner_assignment_matrix.csv`
  - `plans/rewrite/generated/owner_assignment_summary.md`
  - `plans/rewrite/generated/performance_baseline_status.md`
  - `plans/rewrite/generated/rewrite_snapshot.md`
- Supporting automation scripts:
  - `plans/rewrite/scripts/route_auth_auto_verify.py`
  - `plans/rewrite/scripts/rewrite_snapshot.py`
- Historical full draft snapshot (reference only):
  - `plans/rewrite/quay_rewrite.full-backup.2026-02-08.md`

## 3. Current baseline snapshot

Runtime surface discovered from code (static parse):
- API resources (`/api/v1/*`, Flask-RESTful): `176` resource rows (`268` method rows in tracker)
- Registry V2 routes (`/v2/*`): `19` method rows
- Registry V1 routes (`/v1/*`): `24` unique route rows (`26` method rows in tracker)
- Other blueprint routes (web/oauth/webhooks/keys/secscan/realtime/well-known): `84+`
- Dynamic OAuth callback route patterns (`add_url_rule`): `4`
- App-level non-blueprint `add_url_rule` routes: `3` (`/userfiles` GET/PUT, `/_storage_proxy_auth` GET)
- Total method-level route rows in migration tracker: `413`

Worker/process baseline:
- Supervisor programs: `36`
- Queue instances in runtime: `9`
- ORM: Peewee (`data/database.py`)

Authoritative registrations:
- `web.py`
- `registry.py`
- `secscan.py`

## 4. Target architecture (naming)

Terminology used in this plan:
- `quay` CLI: single Go binary with subcommands spanning the full deployment spectrum.
- `quay serve`: run the registry/API/workers in-process (no containers required).
- `quay install`: deploy the Go binary inside containers via Podman Quadlet (replaces mirror-registry).
- `registryd`: Go registry implementation for `/v1/*` and `/v2/*` (served by `quay serve`).
- `api-gateway` (optional): edge routing and cutover control.
- `api-service`: Go implementation for non-registry API surfaces.
- `worker-*`: Go worker processes (separate processes for enterprise; in-process goroutines for mirror mode).

Serving mode presets:

| Mode | Database | Storage | Auth | Cache | TLS | Use case |
|------|----------|---------|------|-------|-----|----------|
| `mirror` | SQLite (embedded) | Local filesystem | Anonymous/none | In-memory | Self-signed (auto) | Air-gapped mirroring, dev |
| `standalone` | PostgreSQL | S3 or local | Database auth | Redis | User-provided or auto | Single-node production |
| `full` | PostgreSQL | S3 + CDN | LDAP/OIDC/OAuth | Redis | Required | Enterprise multi-node |

Each mode is a default config preset; `--config=path` always overrides.

Note on prior naming:
- Earlier drafts used `core-api`. In this plan, use `api-service` to avoid ambiguity.
- The `quay` CLI unifies `mirror-registry`, `quay-distribution-main`, and `config-tool` into a single binary.

## 4.1. Implementation strategy: mirror-first

The mirror mode (`quay serve --mode=mirror`) represents the smallest viable Go implementation of Quay and is targeted as the first deliverable. It validates the core Go registry stack (distribution v3, storage, auth, config) end-to-end in a simplified context (SQLite, local storage, no workers, no Python dependency) before tackling the full enterprise surface.

Benefits of building mirror-first:
- Proves the Go binary, CI pipeline, and distribution v3 integration work end-to-end.
- Delivers immediate value by replacing the current mirror-registry's Ansible/EE complexity.
- Provides a working `quay serve` that becomes the container entrypoint for all deployment profiles.
- Exercises storage, TLS, and config subsystems that are shared with the full enterprise path.
- Failures are low-blast-radius (single-node, no auth, no workers).

Mirror-first does not change the milestone sequence for enterprise Quay (M0-M5). It runs in parallel as an accelerated validation of shared Go infrastructure, with results feeding back into M0 readiness (Go scaffold, CI, storage drivers, config validation).

## 5. Cutover model

Cutover is capability-based, not big-bang service replacement.

Rules:
- One capability has one active owner at a time (`python` or `go`).
- Ownership is explicit in `plans/rewrite/cutover_matrix.md`.
- Switch naming, precedence, and rollback requirements are defined in `plans/rewrite/switch_spec.md`.
- Python stays available as fallback until Go owner is production-stable.
- Disable Python path/capability only after:
  - contract parity tests pass
  - perf guardrails pass
  - canary burn-in succeeds
  - rollback path is confirmed

Examples of capabilities:
- registry pull
- registry push
- manifests/tags/blobs APIs
- v1 route groups
- oauth token flows
- keyserver endpoints
- secscan callbacks
- each worker pipeline

### 5.1. Capability routing implementation

For containerized deployments (`quay install`), nginx acts as the front door during Python/Go coexistence. nginx already routes traffic by URL prefix to `registry_app_server`, `web_app_server`, and `secscan_app_server` via `server-base.conf.jnj`. During migration, Go becomes an additional upstream and prefixes move from Python upstreams to the Go upstream as capabilities migrate.

This approach:
- Requires zero new proxy code — nginx already does this at quay.io scale.
- Preserves production-hardened rate limiting, buffering, and timeout tuning.
- Makes migration a config change (`proxy_pass` target), not a code change.
- Drops away naturally when Python is fully replaced (Go serves directly).

For mirror mode (`quay serve --mode=mirror`), no proxy is needed — Go serves everything directly with no Python dependency.

For Kubernetes deployments, the Quay Operator manages routing between Python and Go services.

## 6. Milestones

### M0: Contracts and inventory gate
Exit criteria:
- `api_surface_inventory.md` complete and reviewed.
- `workers_inventory.md` complete and reviewed.
- `queue_contracts.md` complete and reviewed.
- `data_access_layer_design.md` approved.
- `go_module_strategy.md` approved and Go scaffold/CI checks are green.
- `fips_crypto_migration.md` approved.
- `storage_backend_inventory.md` approved with tracker coverage.
- `registryd_design.md` approved.
- `redis_usage_inventory.md` approved.
- `performance_budget.md` baselines captured.
- `deployment_architecture.md`, `config_tool_evolution.md`, `image_strategy.md`, and `tls_security_posture.md` approved.
- `auth_backend_inventory.md` and `notification_driver_inventory.md` approved.
- `ai_agent_guide.md` approved and workstream task packets created.
- Contract fixture set established for all route families and queues.
- `route_auth_verification.md` shows zero unresolved auth rows.
- route-auth manual backlog is reduced to `<= 50` rows with wave assignments.
- `route_parser_gaps.md` rows are explicitly fixture-tracked.

### MM: Mirror mode (parallel track)

Mirror mode runs as an accelerated parallel track that validates shared Go infrastructure. It does not block or gate enterprise milestones (M1-M5) but feeds results into M0 readiness.

Exit criteria:
- `quay serve --mode=mirror` serves `/v2/*` with local filesystem storage and embedded SQLite.
- `quay install --profile=mirror` deploys a single-container Quadlet with auto-generated TLS.
- `quay config validate` validates mirror-mode configuration.
- `quay migrate` reads existing mirror-registry config and SQLite database.
- `/v2/*` contract tests pass against mirror-mode Go binary.
- Mirror-registry replacement is validated for disconnected/air-gapped installs.
- `config-tool` field group validators are absorbed into `internal/config/`.

Shared infrastructure validated by MM (feeds into M0/M2):
- Go module scaffold and CI pipeline.
- Distribution v3 integration and `/v2` route handlers.
- Local filesystem storage driver.
- Go-native TLS certificate generation.
- Config loading, validation, and mode presets.
- Container image build for Go binary.

### M1: Edge routing and ownership controls
Exit criteria:
- Request routing supports capability ownership switches.
- Canary by org/repo/capability works.
- Instant rollback to Python owner is validated.
- nginx config generation supports Go as an additional upstream during Python coexistence.

### M2: Registry migration (`/v2` + `/v1`)
Exit criteria:
- `/v2/*` parity achieved.
- `/v1/*` parity achieved and explicitly kept supported.
- Python registry handlers can be disabled per capability.

### M3: Non-registry API surface migration
Exit criteria:
- All `/api/v1/*` resources migrated or delegated through Go layer with full parity.
- Blueprint endpoints outside `/api/v1` are migrated (`/oauth*`, `/webhooks`, `/keys`, `/secscan`, `/realtime`, `/.well-known`, required `web` API endpoints).

### M4: Workers and build manager migration
Exit criteria:
- All worker/background processes migrated with preserved semantics.
- Queue payload contracts and retry/idempotency behavior preserved.
- Build manager queue semantics (including ordered queue behavior) preserved.
- Runtime support components in `runtime_support_components.md` are mapped and parity-tested.

### M5: Python deactivation and deployment unification
Exit criteria:
- Cutover matrix shows all capabilities owned by Go.
- Python endpoints/workers disabled in steady state.
- Python remains emergency-only fallback for a bounded period, then removal.
- `quay install` profiles (`standalone`, `ha`) generate Quadlet deployments using Go-only container images.
- nginx removed from default deployment topology (Go serves directly).
- `quay serve` is the container entrypoint for all deployment profiles.

## 7. Global quality gates

For each migrated capability:
- Contract parity tests pass.
- Relevant unit/integration/E2E tests pass.
- Performance budget check passes.
- Security checks pass (including auth behavior parity).
- DB/read-replica/encryption compatibility checks pass for affected capabilities.
- FIPS compatibility checks pass for affected capabilities.
- Observability parity exists (logs/metrics/tracing).
- Runbook and rollback steps are documented.

## 8. Change control

Before modifying scope/contract behavior:
- Update this master (if policy-level change).
- Update affected sub-plan(s).
- Record decision and rationale in `plans/rewrite/decision_log.md`.
