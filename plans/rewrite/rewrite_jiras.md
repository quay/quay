# Quay Go Rewrite — Jira Feature Breakdown

> **Purpose:** Define Jira features covering the full scope of the Quay Python-to-Go rewrite. Each feature is sized for epic decomposition by the engineering team.
>
> **Source:** `plans/rewrite/quay_rewrite.md` and all sub-plan documents.
>
> **Note on PROJQUAY-10515:** The existing mirror-registry Jira (PROJQUAY-10515) covers Phase 1 mirror-registry replacement scope. That scope is incorporated into Feature 4 below. PROJQUAY-10515 can be superseded by this broader feature set, or retained as a child epic of Feature 4.
>
> **Project:** PROJQUAY
> **Labels:** rewrite
> **Component:** quay
>
> **Date:** 2026-03-01

## Jira Feature Keys

| # | Jira Key | Title |
|---|----------|-------|
| F1 | PROJQUAY-10741 | Go Module Bootstrap and CI Infrastructure |
| F2 | PROJQUAY-10742 | Contract Test Framework and Quality Gates |
| F3 | PROJQUAY-10743 | Capability Ownership Switch and Cutover Control Plane |
| F4 | PROJQUAY-10744 | Mirror Mode Registry |
| F5 | PROJQUAY-10745 | Registry Protocol Migration (/v2 + /v1) |
| F6 | PROJQUAY-10746 | REST API Surface Migration (/api/v1) |
| F7 | PROJQUAY-10747 | Blueprint and Non-API Endpoint Migration |
| F8 | PROJQUAY-10748 | Worker and Background Process Migration |
| F9 | PROJQUAY-10749 | Queue Engine and Payload Compatibility |
| F10 | PROJQUAY-10750 | Data Access Layer and Database Evolution |
| F11 | PROJQUAY-10751 | Authentication and Identity Provider Parity |
| F12 | PROJQUAY-10752 | Cryptography, FIPS, and TLS Security Migration |
| F13 | PROJQUAY-10753 | Storage Backend Migration |
| F14 | PROJQUAY-10754 | Redis Usage and Runtime Support Component Migration |
| F15 | PROJQUAY-10755 | Deployment Architecture, Container Image, and Config Evolution |
| F16 | PROJQUAY-10756 | Operational Tooling Migration and Disposition |
| F17 | PROJQUAY-10757 | Route Auth Verification Acceleration |
| F18 | PROJQUAY-10758 | Python Deactivation and Unified Go Deployment |

---

## Implementation Order

Features are organized into **5 phases** that reflect real dependency constraints. Work within a phase can proceed in parallel; work in later phases depends on earlier phases being sufficiently complete.

### Phase 0 — Foundation (start immediately, blocks everything)

These must land first. Nothing else can meaningfully begin without them.

```
┌─────────────────────────────────────────────────────────────┐
│  F1: Go Module Bootstrap & CI Infrastructure                │
│  F17: Route Auth Verification Acceleration                  │
│  F12: Cryptography, FIPS, and TLS Security Migration        │
│       (library selection & approval only — not full impl)   │
└─────────────────────────────────────────────────────────────┘
```

**F1** provides the Go scaffold, CI pipeline, and test wiring that every other feature compiles against. **F17** is an independent planning/verification activity that unblocks safe capability flips later. **F12** library selection (especially AES-CCM) must happen early because it blocks the DAL (F10) and registry signing (F5).

### Phase 1 — Core Infrastructure (start as soon as F1 scaffold is green)

These features build the foundational layers that the migration routes, workers, and protocol handlers depend on. They can proceed in parallel with each other.

```
┌─────────────────────────────────────────────────────────────┐
│  F2:  Contract Test Framework & Quality Gates               │
│  F3:  Capability Ownership Switch Control Plane             │
│  F10: Data Access Layer & Database Evolution                │
│  F4:  Mirror Mode Registry  ← parallel accelerated track   │
└─────────────────────────────────────────────────────────────┘
```

**F2** builds the test harness all capability flips require. **F3** builds the switch control plane for incremental cutover and rollback. **F10** builds the Go DAL that every endpoint and worker needs. **F4** (Mirror Mode) runs as an accelerated parallel track that validates shared Go infrastructure (distribution v3, storage, TLS, config) in a low-risk context; results feed back into the other Phase 1 features.

### Phase 2 — Protocol & Storage (start when DAL and switch control plane are functional)

Registry migration and storage backends are tightly coupled. Auth parity is required for the API surface that follows.

```
┌─────────────────────────────────────────────────────────────┐
│  F5:  Registry Protocol Migration (/v2 + /v1)              │
│  F13: Storage Backend Migration                             │
│  F11: Authentication & Identity Provider Parity             │
│  F14: Redis & Runtime Support Component Migration           │
│  F15: Deployment Architecture, Image, & Config Evolution    │
│       (reference manifests & canary environment)            │
└─────────────────────────────────────────────────────────────┘
```

**F5** and **F13** work together — the registry needs storage drivers. **F11** must be sufficiently complete before the REST API surface can be migrated (Phase 3). **F14** begins here because registry and worker implementations need Redis patterns. **F15** starts building the deployment model so canary environments are ready for Phase 2 validation.

### Phase 3 — API Surface & Workers (start when registry parity is proven and auth is functional)

The large API surface and worker migrations can proceed in parallel once the underlying layers are stable.

```
┌─────────────────────────────────────────────────────────────┐
│  F6:  REST API Surface Migration (/api/v1)                  │
│  F7:  Blueprint & Non-API Endpoint Migration                │
│  F8:  Worker & Background Process Migration                 │
│  F9:  Queue Engine & Payload Compatibility                  │
│  F16: Operational Tooling Migration & Disposition            │
└─────────────────────────────────────────────────────────────┘
```

**F6** and **F7** together cover the full non-registry HTTP surface (~350 route rows). **F8** and **F9** are tightly coupled — workers consume queues. **F16** triages operational scripts in parallel.

### Phase 4 — Unification (start when all capabilities are owner=go)

```
┌─────────────────────────────────────────────────────────────┐
│  F18: Python Deactivation & Unified Go Deployment           │
└─────────────────────────────────────────────────────────────┘
```

This is the final phase: disable Python, remove legacy components, and unify on Go-only deployment.

### Sequencing Diagram

```
Phase 0                Phase 1                Phase 2                Phase 3            Phase 4
───────                ───────                ───────                ───────            ───────
F1 (Go Bootstrap) ──┬─► F2 (Tests) ─────────► required by all Phase 2-3 flips
                    ├─► F3 (Switches) ──────► F5 (Registry) ──────► F6 (REST API) ───► F18
                    ├─► F10 (DAL) ──────────► F5 (Registry)        F7 (Blueprints)     (Python
                    │                         F13 (Storage)         F8 (Workers)         Off)
                    │                         F11 (Auth) ──────────► F6, F7
                    │                         F14 (Redis) ─────────► F8 (Workers)
                    │                         F15 (Deploy) ────────► F15 (continued)
                    │
                    └─► F4 (Mirror) ← parallel track, feeds back into F5/F10/F13

F12 (Crypto/FIPS) ──── library selection in Phase 0, full impl spans Phases 1-3
F17 (Auth Verify) ──── independent, starts Phase 0, completes before Phase 2 flips
F16 (Op Tooling) ───── starts Phase 3, completes by Phase 4
F9 (Queues) ────────── starts Phase 3 with F8 (Workers), tightly coupled
```

### Summary: When to Start Each Feature

| Phase | Feature | Can Start When | Must Complete Before |
|-------|---------|---------------|---------------------|
| 0 | F1: Go Bootstrap & CI | Immediately | Everything else |
| 0 | F17: Route Auth Verification | Immediately | Phase 2 capability flips |
| 0 | F12: Crypto/FIPS (library selection) | Immediately | F10 (DAL encryption) |
| 1 | F2: Contract Tests & Quality Gates | F1 scaffold green | Any capability flip |
| 1 | F3: Switch Control Plane | F1 scaffold green | Any capability flip |
| 1 | F10: Data Access Layer | F1 scaffold green + F12 AES-CCM selected | F5, F6, F7, F8 |
| 1 | F4: Mirror Mode Registry | F1 scaffold green | Independent (parallel track) |
| 2 | F5: Registry Migration | F3 + F10 + F13 functional | M2 exit |
| 2 | F13: Storage Backends | F1 + F12 (CDN signing) | F5 registry migration |
| 2 | F11: Auth & Identity Parity | F1 + F10 | F6, F7 (API needs auth) |
| 2 | F14: Redis & Runtime Components | F1 + F10 | F8 (workers need Redis) |
| 2 | F15: Deployment/Image/Config | F1 + F3 | Canary environments |
| 3 | F6: REST API Migration | F3 + F10 + F11 functional | M3 exit |
| 3 | F7: Blueprint Migration | F3 + F10 + F11 functional | M3 exit |
| 3 | F8: Worker Migration | F3 + F10 + F14 functional | M4 exit |
| 3 | F9: Queue Compatibility | F10 functional | M4 exit (with F8) |
| 3 | F16: Operational Tooling | F1 | M5 exit |
| 4 | F18: Python Deactivation | All F1-F17 complete | Program completion |

---

## Feature 1: Go Module Bootstrap and CI Infrastructure

**Summary:** Initialize the Go module, directory scaffold, CI pipeline, and cross-language build infrastructure that all subsequent Go implementation work depends on.

**Business Value:** Without the Go scaffold and CI gates, no implementation workstream can begin. This is the prerequisite for every other feature in the rewrite.

**Milestone:** M0 (Contracts and Inventory Gate)
**Workstreams:** WS0 (Program Control), partial WS1
**Gates:** G8 (partial)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Go Module Initialization**
   - Create `go.mod` / `go.sum` at repo root (`github.com/quay/quay`, Go 1.24+)
   - Single root module strategy (no multi-module)
   - Pin dependency versions for `distribution/v3`, `chi/v5`, `golang-jwt/v5`, `pgx/v5`, `sqlc`, `go-redis`

2. **Directory Scaffold**
   - Create minimum package scaffold under `internal/`:
     - `internal/dal/` — Data access layer
     - `internal/registry/` — Registry implementation
     - `internal/switch/` — Ownership switch control plane
     - `internal/auth/` — Authentication
     - `internal/storage/` — Storage backends
     - `internal/crypto/` — Cryptography / FIPS
     - `internal/config/` — Configuration loading and validation
   - Create command entrypoints:
     - `cmd/quay/` — Unified CLI binary with subcommands (`serve`, `install`, `worker`, `admin`, `config`)
   - Each package must include at least one `_test.go` file for CI validation

3. **CI Pipeline**
   - Required checks on every PR touching Go code:
     - `go mod tidy` cleanliness (no diff)
     - `go test ./...`
     - `go vet ./...`
     - `golangci-lint run` (pinned version and config)
   - Staged tiers:
     - Fast tier (required): unit tests + vet
     - Slow tier (required before merge): contract suites under `tests/rewrite/contracts/`
   - Multi-arch build matrix validation (`x86_64`, `aarch64`, `ppc64le`, `s390x`)

4. **Cross-Language Contract Test Wiring**
   - Go test harness reads fixture artifacts generated from Python-oracle runs
   - Produces normalized result JSON for diffing
   - Annotates tracker rows with `test_file`, `last_run_commit`, `last_passed_at`
   - At least one contract test package runnable in CI before M0 exit

### Acceptance Criteria
- `go.mod` and `go.sum` exist at repo root and pass `go mod tidy` check
- Minimum package scaffold compiles (`go build ./...`)
- CI runs `go test ./...`, `go vet ./...`, and `golangci-lint` on every Go PR
- At least one contract test package is runnable in CI
- Security review complete for all dependencies with C bindings

### Dependencies
- None (this is the root dependency for all other features)

### Plan References
- `plans/rewrite/go_module_strategy.md`
- `plans/rewrite/m0_readiness_checklist.md`

---

## Feature 2: Contract Test Framework and Quality Gates

**Summary:** Build the test harness and contract test suites that prove behavior parity for every migrated endpoint, worker, queue, and runtime component. Define and enforce the quality gates that control capability ownership flips.

**Business Value:** No capability can be flipped from Python to Go without passing contract tests, performance budgets, and rollback validation. This framework is the safety net for the entire migration.

**Milestone:** M0 (fixture establishment), cross-cutting through M5
**Workstreams:** WS1 (Contract Fixtures and Test Harness), WS0 (Program Control and Evidence)
**Gates:** G4 (Test Implementation), G15 (Performance Baselines)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Route Contract Test Suite**
   - Input/output parity tests: status codes, headers, body schema
   - Auth parity tests: anonymous, session, OAuth, JWT for each route
   - Error model parity tests
   - Feature-gated route presence/absence parity
   - Generate and maintain `route_contract_tests.csv` with golden fixture IDs, parity test IDs, and performance budget IDs
   - Cover all 413 method-level route rows

2. **Queue and Worker Contract Test Suite**
   - Payload schema compatibility in mixed Python/Go mode
   - Retry, lease extension, incomplete/complete semantics
   - Ordered build queue semantics
   - Idempotency under duplicate delivery
   - Generate and maintain `queue_worker_contract_tests.csv` and `worker_process_contract_tests.csv`

3. **Performance Budget Enforcement**
   - Capture Python baselines for 14 consecutive days on representative workloads (P50/P95/P99, error rate, saturation, queue lag)
   - Enforce budget IDs: `PB-REG-AUTH`, `PB-REG-PULL`, `PB-REG-PUSH`, `PB-API-HOT`, `PB-WORKER-LAG`, `PB-DB-SAFETY`
   - Pre-cutover full budget runs; canary checks at 1h/6h/24h; daily post-cutover checks
   - Performance threshold breach blocks owner flip; severe regression triggers rollback

4. **Rollback Validation Framework**
   - Route-owner and worker-owner rollback drill tests
   - Replay and reconciliation checks after rollback
   - Automated rollback drill exercises for each capability family

5. **Evidence and Signoff System**
   - Capability-level evidence packets (tests, canary results, rollback drills, performance budgets)
   - Gate dashboard updates and release go/no-go records
   - Signoff workflow: promote `verified-source-anchored` rows to `verified` with owner signoff and test evidence
   - Traceability fields on all tracker rows

### Acceptance Criteria
- Every route/worker/queue/runtime tracker row maps to a runnable contract test
- Python baselines captured and published for all `PB-*` budget IDs
- Rollback drill framework exercised for at least one capability family
- Evidence packet template defined and linked from gate dashboard
- No capability flip to `go` without: parity tests pass, queue compat tests pass, auth-mode matrix coverage pass, performance budgets pass, rollback drill pass

### Dependencies
- Feature 1 (Go Module Bootstrap) — test harness requires Go scaffold
- Feature 3 (Switch Control Plane) — rollback drills require owner switches

### Plan References
- `plans/rewrite/test_strategy.md`
- `plans/rewrite/test_implementation_plan.md`
- `plans/rewrite/performance_budget.md`
- `plans/rewrite/signoff_workflow.md`
- `plans/rewrite/signoff_schedule.md`
- `plans/rewrite/program_gates.md`

---

## Feature 3: Capability Ownership Switch and Cutover Control Plane

**Summary:** Implement the control plane that enables incremental, per-capability Python-to-Go ownership cutover with instant rollback. This includes route-owner switches, worker-owner switches, canary selectors, and the global emergency fallback.

**Business Value:** The switch control plane is the mechanism that makes the migration safe and reversible. Without it, the team cannot incrementally roll out Go capabilities or instantly roll back on regression.

**Milestone:** M1 (Edge Routing and Ownership Controls)
**Workstreams:** WS2 (Ownership Switch Control Plane)
**Gates:** G1 (complete design), implementation required for M1
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Route Owner Resolution**
   - 3-level precedence: route-method override → capability override → family default → global default (`python`)
   - Switch naming: `ROUTE_OWNER_ROUTE_<ROUTE_ID>`, `ROUTE_OWNER_CAP_<CAPABILITY>`, `ROUTE_OWNER_FAMILY_<FAMILY>`
   - 12 route families: `REGISTRY_V2`, `REGISTRY_V1`, `API_V1`, `OAUTH`, `WEBHOOKS`, `KEYS`, `SECSCAN`, `REALTIME`, `WELLKNOWN`, `OTHER`, plus sub-capability overrides
   - Unknown owner values fail closed to `python`

2. **Worker Owner Resolution**
   - Per-program switches: `WORKER_OWNER_<PROGRAM_NAME>` (value: `python` | `go` | `off`)
   - Covers all 36 supervisor programs
   - Integration with existing `QUAY_OVERRIDE_SERVICES` (owner switch takes precedence; emit deprecation warning)

3. **Canary Selectors**
   - Independent selectors: `ROUTE_CANARY_ORGS`, `ROUTE_CANARY_REPOS`, `ROUTE_CANARY_USERS`, `ROUTE_CANARY_PERCENT`
   - Canary by org/repo/capability validated in staging

4. **Global Emergency Fallback**
   - `MIGRATION_FORCE_PYTHON=true` forces all routes and workers to Python owner
   - Single change operation for atomic rollback
   - No code deploy required for rollback

5. **Switch Transport and Propagation**
   - Stage A (Bootstrap): Environment-backed values at startup for early bring-up/staging
   - Stage B (Production Required): Runtime dynamic config provider with periodic refresh
   - Max propagation delay: < 30 seconds
   - Last-known-good cache required
   - Monotonic versioning required

6. **Observability and Audit**
   - Every owner decision emits metric label (`owner=python|go`) with route/process ID
   - Switch parsing failures logged and alerted but don't break request handling
   - Audit log for all owner changes

7. **nginx Upstream Routing (Containerized Deployments)**
   - nginx already routes by URL prefix to `registry_app_server`, `web_app_server`, `secscan_app_server`
   - Add Go as additional upstream; migrate prefixes from Python to Go as capabilities migrate
   - Config generation supports Go upstreams during Python/Go coexistence
   - For Kubernetes deployments, Quay Operator manages routing between Python and Go services

### Acceptance Criteria
- Route owner resolution with full 3-level precedence works in staging
- Worker owner resolution works for all 36 programs
- Canary selectors route traffic correctly for scoped cohorts
- Emergency fallback (`MIGRATION_FORCE_PYTHON`) proven in staging
- Ownership flip and rollback work without code deploy
- Propagation delay < 30 seconds measured and validated
- Observability metrics emitted for all owner decisions
- nginx config generation supports Go upstream

### Dependencies
- Feature 1 (Go Module Bootstrap) — switch library lives in `internal/switch/`

### Plan References
- `plans/rewrite/switch_spec.md`
- `plans/rewrite/switch_transport_design.md`
- `plans/rewrite/cutover_matrix.md`

---

## Feature 4: Mirror Mode Registry

**Summary:** Build the mirror mode (`quay serve --mode=mirror`) as the first end-to-end Go deliverable, replacing the current OpenShift Mirror Registry (OMR) with a lightweight single-binary registry for disconnected/air-gapped environments. This validates the core Go registry stack before tackling the full enterprise surface.

**Business Value:** Delivers immediate value by replacing the current OMR's complex Ansible/EE installation (8GB+ RAM, SSH keys, Podman volumes) with a single Go binary (~100-200MB memory). Resolves critical OMR issues: SQLite locking, Podman volume lock exhaustion, complex upgrades. Validates shared Go infrastructure (distribution v3, storage, TLS, config) in a low-blast-radius context.

**Milestone:** MM (Mirror Mode — parallel track)
**Supersedes/Incorporates:** PROJQUAY-10515
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Core Registry Write Operations**
   - Enable push operations using distribution/distribution v3.0.0
   - Write manifest bytes to filesystem storage
   - Support chunked blob uploads
   - Enable manifest/blob deletion for GC
   - Support atomic blob finalization
   - Pass OCI Distribution Spec conformance tests

2. **`quay serve --mode=mirror`**
   - Serve `/v2/*` with local filesystem storage and embedded SQLite
   - Anonymous/none authentication mode
   - In-memory cache (no Redis dependency)
   - Self-signed TLS (auto-generated)
   - No workers, no Python dependency
   - Single-process Go binary

3. **Authentication and Access Control**
   - HTTP Basic authentication for push/pull
   - Create initial admin user with generated password
   - Secure credential storage (htpasswd or embedded)
   - Configurable anonymous read access

4. **CLI Tooling**
   - `quay install --profile=mirror` — deploy single-container Quadlet with auto-generated TLS
   - `quay config validate` — validate mirror-mode configuration
   - `quay migrate` — read existing mirror-registry config and SQLite database
   - Start/stop service lifecycle management
   - Upgrade: binary replacement
   - Uninstall: removal of registry data
   - TLS cert generation: auto-generate self-signed or accept user-provided
   - Packaging: tarball with binary + container image

5. **Storage Architecture**
   - Filesystem storage (default): pure filesystem via distribution/distribution (no database for blob storage)
   - Local filesystem storage driver validated end-to-end
   - Standard filesystem storage instead of Podman named volumes

6. **Migration and Compatibility**
   - Data migration tool: migrate images from SQLite-based OMR
   - CLI compatibility: match existing `--quayHostname`, `--quayRoot`, etc. flags
   - `oc-mirror` compatibility: work seamlessly with oc mirror plugin
   - `config-tool` field group validators absorbed into `internal/config/`

7. **Contract Tests for Mirror Mode**
   - `/v2/*` contract tests pass against mirror-mode Go binary
   - Mirror-registry replacement validated for disconnected/air-gapped installs

### Acceptance Criteria
- `quay serve --mode=mirror` serves `/v2/*` pull and push with filesystem storage and SQLite
- `quay install --profile=mirror` deploys single-container Quadlet with auto-generated TLS
- `quay config validate` validates mirror-mode configuration
- `quay migrate` reads existing OMR config and database
- `/v2/*` contract tests pass against mirror-mode binary
- OCI Distribution Spec conformance tests pass
- Memory footprint < 200MB under typical mirror workload
- Disconnected/air-gapped install validated without network access

### Dependencies
- Feature 1 (Go Module Bootstrap) — Go scaffold must exist
- Shares infrastructure with Feature 5 (Registry Migration) — distribution v3, storage, auth

### Plan References
- `plans/rewrite/quay_rewrite.md` §4.1 (mirror-first strategy)
- `plans/rewrite/registryd_design.md`
- PROJQUAY-10515 (existing mirror-registry Jira — incorporated here)
- `https://gist.github.com/jbpratt/f23cef1dcabcac3dec55ec55578abd9a` (unified CLI design)

---

## Feature 5: Registry Protocol Migration (/v2 + /v1)

**Summary:** Migrate the full registry protocol surface — 19 `/v2/*` method rows and 26 `/v1/*` method rows — from Python to Go with complete behavior parity, including chunked uploads, schema1 signing, and mixed-runtime upload session handling.

**Business Value:** The registry protocol is Quay's core value proposition. Full parity ensures no disruption to container image push/pull workflows while enabling the performance and reliability benefits of the Go implementation.

**Milestone:** M2 (Registry Migration)
**Workstreams:** WS3 (Registry Migration)
**Gates:** G11 (registryd architecture)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **`/v2/*` Pull Path Parity**
   - Manifest GET (all media types including OCI and Docker schema2)
   - Blob GET and HEAD
   - Tags list
   - Catalog (if enabled)
   - Referrers API
   - Auth token exchange (`/v2/auth`)
   - Feature-gated route behavior (referrers, v2 advertise)

2. **`/v2/*` Push Path Parity**
   - Manifest PUT
   - Blob upload initiation (POST)
   - Chunked blob upload (PATCH with Content-Range)
   - Blob upload finalization (PUT with digest)
   - Cross-mount blob operations
   - Blob DELETE

3. **Upload State Machine and Cross-Runtime Handling**
   - Upload session persistence and resume across restarts
   - Range validation with monotonic offset guarantee
   - **Upload hasher state serialization** (critical dual-runtime blocker):
     - M2-M3: Pin upload ownership by UUID (no cross-runtime continuation)
     - M4+: Introduce non-pickle cross-runtime format (JSON/protobuf)
     - Reject cross-runtime session continuation with explicit retryable error during pinning phase
   - Failure behavior parity: range mismatch status codes, digest mismatch leaves no partial state, canceled sessions cannot resume

4. **`/v1/*` Full Parity**
   - Images GET/PUT/DELETE
   - Tags GET/PUT/DELETE
   - Search
   - Users (login/auth)
   - `/v1/*` remains supported (not deprecated in migration scope)
   - Existing `X-Docker-Token` auth contracts preserved

5. **Schema1 Signing and Verification**
   - RS256 signing and verification for legacy schema1 manifests
   - Deterministic serialization/signing compatible with existing clients
   - Cross-runtime fixture tests: Python-signed payload verifies in Go, Go-signed payload verifies in Python
   - Fixture format: `tests/rewrite/contracts/registry/schema1/fixtures/<name>.json`

6. **Observability and Control Integration**
   - Per-route-family parity metrics (v1, v2)
   - Upload state transition counters and error-code histograms
   - Auth-scope rejection counters by reason
   - Integration with owner switches from switch_spec.md
   - Labels: `route_family`, `capability_owner`, `status_class`, `error_reason`

### Acceptance Criteria
- All 19 `/v2/*` method rows pass contract parity tests against Python oracle
- All 26 `/v1/*` method rows pass contract parity tests
- Chunked upload resume/finalize works within single runtime (Go-to-Go)
- Upload pinning rejects cross-runtime continuation with retryable error
- Schema1 cross-runtime sign/verify tests pass
- Performance budgets `PB-REG-AUTH`, `PB-REG-PULL`, `PB-REG-PUSH` pass
- Python registry handlers can be disabled per capability after parity validation
- Rollback to Python owner validated under canary traffic

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 3 (Switch Control Plane) — route owner switches required for cutover
- Feature 10 (Data Access Layer) — registry DAL operations
- Feature 12 (Cryptography/FIPS) — schema1 signing, JWT token handling
- Feature 13 (Storage Backends) — storage driver layer

### Plan References
- `plans/rewrite/registryd_design.md`
- `plans/rewrite/generated/route_migration_tracker.csv` (registry rows)
- `plans/rewrite/generated/route_family_cutover_sequence.md`

---

## Feature 6: REST API Surface Migration (/api/v1)

**Summary:** Migrate all 268 `/api/v1/*` Flask-RESTful resource method rows to the Go `api-service`, preserving all request/response contracts, authentication behavior, and feature-gated route presence.

**Business Value:** The REST API powers the Quay UI, CLI tools, and third-party integrations. Full parity ensures uninterrupted management and administration workflows.

**Milestone:** M3 (Non-Registry API Surface Migration)
**Workstreams:** WS4 (API and Blueprint Endpoint Migration)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **API Resource Migration — User and Organization Management**
   - User CRUD, settings, permissions
   - Organization CRUD, teams, members, billing
   - Robot accounts and credentials
   - Quota management (including superuser quota routes with multi-URL class resources)

2. **API Resource Migration — Repository Management**
   - Repository CRUD, settings, visibility
   - Repository notifications (create/update/delete/test)
   - Repository permissions (user/team)
   - Repository images, tags, manifests
   - Build triggers and build history

3. **API Resource Migration — Security and Scanning**
   - Vulnerability scanning endpoints
   - Image security status
   - Repository security notifications

4. **API Resource Migration — Superuser and Administration**
   - Superuser management endpoints
   - Global readonly superuser behavior
   - System logs and usage statistics
   - Service keys management
   - Registry state endpoints

5. **API Resource Migration — Discovery and Metadata**
   - API discovery endpoint
   - Error detail endpoints
   - Plans and billing endpoints
   - Global messages endpoints
   - App-specific token endpoints

6. **Feature-Gated Route Behavior**
   - Migrate all `show_if` / `route_show_if` feature gate expressions
   - Preserve route presence/absence behavior based on runtime configuration
   - Feature gate inventory coverage from `feature_gate_inventory.md`

7. **Auth Mode Parity**
   - Preserve per-route auth mode behavior from `auth_mode_matrix.md`
   - Route auth checklist completion for all `/api/v1` rows

### Acceptance Criteria
- All 268 `/api/v1` method rows pass contract parity tests
- Feature-gated route presence/absence matches Python behavior for all configurations
- Auth mode parity verified for every route
- Performance budget `PB-API-HOT` passes for hot endpoints
- Rollback to Python owner validated

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 3 (Switch Control Plane) — `ROUTE_OWNER_FAMILY_API_V1`
- Feature 10 (Data Access Layer)
- Feature 11 (Authentication Parity)

### Plan References
- `plans/rewrite/api_surface_inventory.md`
- `plans/rewrite/generated/route_migration_tracker.csv` (api-v1 rows)
- `plans/rewrite/generated/feature_gate_inventory.md`
- `plans/rewrite/generated/auth_mode_matrix.md`

---

## Feature 7: Blueprint and Non-API Endpoint Migration

**Summary:** Migrate all non-registry, non-`/api/v1` HTTP endpoints including OAuth flows, webhooks, key server, security scanning callbacks, realtime SSE, well-known URIs, web blueprint contract endpoints, and app-level routes.

**Business Value:** These endpoints support critical integration workflows (OAuth login, webhook-driven CI/CD, security scanning feedback), SSO/federation, and operational health checking. Incomplete migration would leave gaps in the unified Go deployment.

**Milestone:** M3 (Non-Registry API Surface Migration)
**Workstreams:** WS4 (API and Blueprint Endpoint Migration)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **OAuth Endpoint Migration**
   - `/oauth2/*` — login callback, attach callback, CLI callback, captcha callback
   - `/oauth1/*` — Bitbucket callback
   - Dynamic OAuth callback route patterns (`add_url_rule` at startup)
   - OAuth grant endpoints from `web` blueprint
   - Token exchange and refresh flows

2. **Webhook Endpoint Migration**
   - `/webhooks/*` — Stripe webhooks, build trigger webhooks
   - Payload signature verification
   - Error and retry behavior

3. **Key Server Endpoint Migration**
   - `/keys/*` — service key API endpoints
   - Key rotation and verification behavior

4. **Security Scanning Callback Migration**
   - `/secscan/*` — Clair callback and status endpoints
   - Feature-gated behavior (`SECURITY_*` feature flags)

5. **Realtime and SSE Migration**
   - `/realtime/*` — Server-Sent Events subscriptions
   - Connection lifecycle and heartbeat behavior

6. **Well-Known URI Migration**
   - `/.well-known/*` — capabilities endpoint, password-change redirect

7. **Web Blueprint Contract Endpoints**
   - `/config`, `/csrf_token`, health routes
   - OAuth grant endpoints
   - Initialize endpoint
   - Build/log link endpoints
   - 65-66 route rows in web blueprint requiring triage and migration

8. **App-Level Non-Blueprint Routes**
   - `/userfiles/*` — file serving/upload semantics (from `data/userfiles.py`)
   - `/_storage_proxy_auth` — storage proxy JWT validation (from `storage/downloadproxy.py`)

### Acceptance Criteria
- All 84+ non-API, non-registry blueprint route rows migrated with parity tests
- Dynamic OAuth callback patterns preserved
- App-level `add_url_rule` routes (`/userfiles`, `/_storage_proxy_auth`) migrated
- Web blueprint route count reconciliation resolved (66 vs 65)
- Parser-gap routes canonicalized into stable fixture IDs

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 3 (Switch Control Plane) — family switches: `OAUTH`, `WEBHOOKS`, `KEYS`, `SECSCAN`, `REALTIME`, `WELLKNOWN`, `OTHER`
- Feature 10 (Data Access Layer)
- Feature 11 (Authentication Parity) — OAuth flows

### Plan References
- `plans/rewrite/api_surface_inventory.md`
- `plans/rewrite/generated/non_blueprint_route_inventory.md`
- `plans/rewrite/generated/route_parser_gaps.md`

---

## Feature 8: Worker and Background Process Migration

**Summary:** Migrate all 36 supervisor-managed background processes from Python to Go, including 8 queue workers, the build manager, scheduled workers, and service-support processes, preserving all trigger semantics, side effects, and concurrency invariants.

**Business Value:** Workers handle critical background operations: garbage collection, storage replication, security scan processing, build orchestration, and notification delivery. Parity ensures operational continuity and data integrity.

**Milestone:** M4 (Workers and Build Manager Migration)
**Workstreams:** WS5 (Worker and Build-Manager Migration)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Queue Worker Migration (8 workers)**
   - `chunkcleanupworker` — Swift chunk cleanup
   - `storagereplication` — image storage replication across locations
   - `repositorygcworker` — repository garbage collection (uses `LARGE_GARBAGE_COLLECTION` global lock)
   - `namespacegcworker` — namespace garbage collection (uses `LARGE_GARBAGE_COLLECTION` global lock)
   - `notificationworker` — notification delivery
   - `securityscanningnotificationworker` — security scan notification processing
   - `proxycacheblobworker` — proxy cache blob management
   - `exportactionlogsworker` — action log export

2. **Build Manager Migration**
   - Build orchestration with ordered queue claims (`ordering_required=True`)
   - Custom retry/timeout handling
   - `BuildCanceller` runtime support component
   - Build queue lifecycle: item bodies embedded into orchestrator state, specific requeue paths

3. **Scheduled and Timer-Based Worker Migration**
   - Workers triggered by scheduler/timer rather than queue
   - Startup guard semantics: feature flags, runtime conditions (account recovery mode, readonly/disable pushes, storage engine checks)

4. **Service-Support Process Migration**
   - `PrometheusPlugin` — background push thread and request metrics
   - `UserEventsBuilderModule` — realtime pub/sub semantics
   - `PullMetricsBuilderModule` — async pull tracking + Redis script + thread pool
   - `Analytics` — optional Mixpanel queue + sender thread
   - `MarketplaceUserApi` / `MarketplaceSubscriptionApi` — external entitlement lookup

5. **Notification Delivery Parity**
   - 6 notification delivery methods: in-app, email, webhook, Flowdock, HipChat, Slack
   - 11 registered event types: `repo_push`, `repo_mirror_sync_*`, `vulnerability_found`, `build_*`, `repo_image_expiry`
   - Event-to-method routing configuration compatibility
   - Outbound payload template parity against Python fixtures
   - Idempotent delivery under duplicate queue delivery

6. **Worker Concurrency and Locking**
   - `QueueWorker` watchdog + `extend_processing` semantics
   - GC workers: global lock behavior, long reservations
   - Preserve feature flag and runtime condition startup guards
   - `QUAY_SERVICES` / `QUAY_OVERRIDE_SERVICES` interaction with owner switches

### Acceptance Criteria
- All 36 supervisor programs tracked with migration status (owner=go or retired-approved with decision entry)
- Queue worker claim/complete/retry semantics preserved
- Build manager ordered queue and orchestrator state semantics preserved
- GC workers global lock and reservation behavior preserved
- All 6 notification delivery methods and 11 event types pass parity tests
- Worker throughput and queue lag within `PB-WORKER-LAG` budget
- Each worker rollback demonstrated: flip `WORKER_OWNER_<PROGRAM>` back to python

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 3 (Switch Control Plane) — `WORKER_OWNER_<PROGRAM>` switches
- Feature 9 (Queue Engine) — queue semantics
- Feature 10 (Data Access Layer) — DB operations
- Feature 14 (Redis) — pub/sub, locks, metrics patterns

### Plan References
- `plans/rewrite/workers_inventory.md`
- `plans/rewrite/notification_driver_inventory.md`
- `plans/rewrite/runtime_support_components.md`
- `plans/rewrite/generated/worker_migration_tracker.csv`
- `plans/rewrite/generated/worker_phase_sequence.md`

---

## Feature 9: Queue Engine and Payload Compatibility

**Summary:** Ensure the 9 runtime queue instances maintain full behavioral parity during mixed Python/Go producer/consumer operation and after full Go cutover. Preserve claim-by-CAS, retry semantics, lease extension, and ordered mode for builds.

**Business Value:** Queues connect API endpoints to background workers. Mixed-mode operation is required throughout the migration. Payload or behavioral incompatibility would cause data loss, build failures, or GC corruption.

**Milestone:** M4 (Workers and Build Manager Migration)
**Workstreams:** WS6 (Queue Engine and Payload Compatibility)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Queue Engine Behavioral Parity**
   - At-least-once delivery preserved
   - Claim-by-update via `id + state_id` compare-and-swap
   - Claim decrements `retries_remaining`
   - `complete` removes item; `incomplete` supports retry restoration with `retry_after`
   - Lease extension via `extend_processing`
   - Ordered mode (`ordering_required=True`) for build manager
   - `state_id` regeneration and CAS behavior validated under contention

2. **Payload Schema Compatibility (9 queues)**
   - `chunk_cleanup` — `location`, `path`, optional `uuid`
   - `imagestoragereplication` — `namespace_user_id`, `storage_id`
   - `proxycacheblob` — `digest`, `repo_id`, `username`, `namespace`
   - `dockerfilebuild` — `build_uuid`, `pull_credentials`
   - `notification` — `notification_uuid`, `event_data`, `performer_data`
   - `secscanv4` — `notification_id`, worker-maintained `current_page_index`
   - `exportactionlogs` — `export_id`, `repository_id`, `namespace_id`, `namespace_name`, `repository_name`, `start_time`, `end_time`, `callback_url`, `callback_email`
   - `repositorygc` — `marker_id`, `original_name`
   - `namespacegc` — `marker_id`, `original_username`
   - Validate both presence and absence of optional payload fields in mixed-producer scenarios

3. **Mixed-Mode Producer/Consumer Testing**
   - Python produces → Go consumes (and vice versa) for all 9 queues
   - Verify JSON payload compatibility (Python loosely typed → Go validated)
   - Test `all_queues` list gap: `proxy_cache_blob_queue`, `secscan_notification_queue`, `export_action_logs_queue` excluded from namespace-deletion cleanup — preserve or explicitly change this behavior

4. **Route-to-Producer Dependency Evidence**
   - Verified route-to-producer call-path evidence for indirect producers
   - Route→queue dependency matrix (`route_worker_dependency_matrix.csv`)
   - Cutover sequencing: routes and their dependent workers must be sequenced correctly

### Acceptance Criteria
- Queue contract and replay tests pass in mixed mode (Python producer + Go consumer, Go producer + Python consumer) for all 9 queues
- Queue tests pass in go-only mode for all 9 queues
- Ordered queue behavior preserved for build manager
- CAS contention tests pass
- Namespace-deletion cleanup behavior for excluded queues explicitly documented and tested
- Route-to-producer dependency evidence verified

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 10 (Data Access Layer) — `QueueItem` table operations

### Plan References
- `plans/rewrite/queue_contracts.md`
- `plans/rewrite/queue_cutover_dependencies.md`
- `plans/rewrite/generated/queue_inventory.md`
- `plans/rewrite/generated/queue_payload_inventory.md`
- `plans/rewrite/generated/route_worker_dependency_matrix.md`

---

## Feature 10: Data Access Layer and Database Evolution

**Summary:** Implement the Go data access layer (DAL) replacing the Python Peewee ORM, including connection pooling, retry logic, read-replica routing, field-level encryption compatibility, and schema evolution tooling for mixed Python/Go runtime operation.

**Business Value:** The DAL underpins every other feature. Incorrect behavior causes data corruption, inconsistent reads, or encryption failures. Mixed-runtime database compatibility is required throughout the migration period.

**Milestone:** M0 (design approval), cross-cutting through M5
**Workstreams:** WS8 (Data Layer and Schema Evolution)
**Gates:** G8 (Data Access Layer Architecture)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Core DAL Architecture**
   - Tech stack: `pgx/v5` + `pgxpool` (PostgreSQL), `sqlc` for code generation
   - Package layout: `internal/dal/{dbcore, readreplica, crypto, repositories, testkit}`
   - Connection lifecycle: pooling on by default, context carries read intent and replica flags
   - Mirror mode: SQLite DAL wiring via `modernc.org/sqlite` or `mattn/go-sqlite3`

2. **Read-Replica Routing**
   - Randomized healthy-replica selection
   - Short-lived bad-host quarantine
   - Explicit bypass support (`disallow_replica_use`)
   - 1 retry on replica failure to primary for reads; 0 retries for writes unless idempotent
   - Replica routing dashboard

3. **Field-Level Encryption Compatibility**
   - AES-CCM encryption/decryption compatible with Python `data/fields.py`
   - `convert_secret_key` must byte-for-byte replicate Python's `itertools.cycle` padding (3 parsing modes: integer string, UUID hex, raw bytes)
   - Golden test corpus: Python-encrypted → Go-decrypted, Go-encrypted → Python-decrypted
   - Bcrypt credential hashing parity (`golang.org/x/crypto/bcrypt`)

4. **Query Surface Implementation**
   - Complete query surface inventory before WS8 starts
   - Classification: static sqlc (~60-70%), conditional Go builder (~20-25%), raw pgx (~5-10%)
   - Repository pattern with interfaces + postgres sqlc implementations
   - Enum table caching: load all lookup tables at startup with process-lifetime TTL

5. **Delete Semantics and Cascade Ordering**
   - Delete cascade ordering for User (28+ dependents) and Repository (19+ dependents)
   - Delete-semantics parity hooks
   - Cleanup callback behavior preserved

6. **Schema Evolution Tooling**
   - Expand → migrate → contract evidence for schema changes
   - Schema drift CI gate operational
   - `sqlalchemybridge.py` retirement tracked (cannot be removed until Go migration tooling passes M5 switchover gate per db_migration_policy.md §10.7)

7. **Mixed-Runtime Database Consistency**
   - Queue optimistic concurrency parity (`state_id` regeneration + CAS behavior)
   - Transaction boundary parity
   - Connection pool and query error metrics
   - Mixed Python/Go runtime passes DB consistency and rollback checks

### Acceptance Criteria
- Go DAL scaffold compiles in CI with pgx/sqlc dependencies
- High-risk repository area validated end-to-end (read/write/retry/rollback)
- Read-replica routing works: normal, degraded, bypass modes
- Encryption compatibility tests green in FIPS-on and FIPS-off environments
- `convert_secret_key` test vectors pass for all 3 parsing modes
- Bcrypt credential verification parity tests green
- Delete cascade ordering validated for User and Repository
- Queue CAS and `state_id` regeneration validated under contention
- Schema drift CI gate operational
- Performance budget `PB-DB-SAFETY` passes (no new full scans, P99 within threshold)

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 12 (Cryptography/FIPS) — AES-CCM library selection

### Plan References
- `plans/rewrite/data_access_layer_design.md`
- `plans/rewrite/db_migration_policy.md`

---

## Feature 11: Authentication and Identity Provider Parity

**Summary:** Migrate all 6 identity provider backends and 8 authentication mechanisms from Python to Go, preserving login flows, team synchronization, federated identity linking, and the dual-pipeline auth architecture.

**Business Value:** Authentication is the security boundary for Quay. Any regression breaks user login, CI/CD robot access, or SSO federation. Enterprise customers depend on LDAP, OIDC, and Keystone integration.

**Milestone:** M3 (required for API migration), cross-cutting
**Workstreams:** WS7 (Auth and Identity Parity)
**Gates:** G14 (Auth Backend + Notification Parity)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Identity Provider Backend Migration (6 backends)**
   - Database auth
   - LDAP (with team sync)
   - External JWT
   - Keystone v2/v3
   - AppToken
   - OIDC (with team sync, federated identity linking)
   - Per-backend: Go library/runtime mapping, configuration compatibility, user-linking/team-sync behavior, failure/fallback behavior

2. **Auth Mechanism Migration — Pipeline A (7 mechanisms)**
   - Basic auth
   - Session/cookie auth
   - OAuth flows
   - SSO JWT (`ssojwt`)
   - Signed grant flows
   - Credential helper/service flows
   - Federated robot auth (`federated`)
   - All produce `ValidateResult`-style identity contexts

3. **Auth Mechanism Migration — Pipeline B (Registry JWT)**
   - `process_registry_jwt_auth` — builds signed identity context directly
   - Implement as distinct middleware chain
   - Do NOT force Pipeline A and B through one abstraction

4. **Auth Mode Matrix Verification**
   - Verify auth mode for all 413 route rows against `auth_mode_matrix.md`
   - Ensure per-route auth mode behavior matches Python implementation

5. **Provider Conformance Tests**
   - Backend login/refresh/logout parity tests per provider
   - Federated identity linking tests
   - Team synchronization behavior tests
   - Negative-path tests: provider outage, bad claims, mapping conflicts
   - Separate test suites for Pipeline A vs Pipeline B behavior

### Acceptance Criteria
- All 6 backends mapped with Go library decisions and owner assignments
- All 8 auth mechanisms mapped to middleware/validator owners with parity test IDs
- Conformance tests pass for all enabled backends
- Auth regression dashboard includes per-backend failure metrics
- No auth regressions in canary and signoff rows verified
- Pipeline A and Pipeline B identity context propagation independently validated

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 10 (Data Access Layer) — user/credential DB operations
- Feature 12 (Cryptography/FIPS) — JWT signing/verification, bcrypt

### Plan References
- `plans/rewrite/auth_backend_inventory.md`
- `plans/rewrite/generated/auth_mode_matrix.md`
- `plans/rewrite/generated/route_auth_verification.md`

---

## Feature 12: Cryptography, FIPS, and TLS Security Migration

**Summary:** Migrate all 13 cryptographic primitive areas from Python to Go with FIPS-compatible implementations. Define and execute the TLS termination model, cipher policy, and security posture for Go services.

**Business Value:** FIPS compliance is a hard requirement for government and regulated deployments. Cryptographic regressions (encryption, signing, token validation) would compromise security and break cross-runtime compatibility during the migration period.

**Milestone:** M0 (library selection and approval), cross-cutting through M5
**Workstreams:** WS9 (Platform Security, TLS, and FIPS)
**Gates:** G9 (FIPS/Crypto), G13 (TLS)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **AES-CCM Encryption/Decryption (High Risk)**
   - DB field encryption compatibility with Python `data/fields.py`
   - Go 1.24's `GOFIPS140` covers AES-GCM but NOT AES-CCM
   - CCM mode operates outside validated module boundary
   - Library selection and FIPS auditor acceptance required
   - Options: standalone CCM wrapping `crypto/aes`, `pion/dtls` CCM, or migrate to AES-GCM with data migration
   - `convert_secret_key` byte-for-byte replication of Python's `itertools.cycle` key padding

2. **JWT and Signing Primitives (High Risk)**
   - Registry bearer token: JWT RS256 via `golang-jwt/jwt/v5`
   - Schema1 signing: JWS RS256 via JOSE library
   - OIDC JWT verification: RS256 validation
   - Secscan API auth: JWT HS256
   - PKCE challenge: SHA-256 + base64url
   - All must work in FIPS mode

3. **CDN Signing Algorithm Compatibility**
   - CloudFront: RSA PKCS1v15 + SHA1 (high risk in FIPS-strict — requires policy decision)
   - CloudFlare: RSA PKCS1v15 + SHA256
   - Akamai: HMAC EdgeAuth token
   - Swift temp URL: HMAC-SHA1 (high risk in FIPS-strict)

4. **Legacy Symmetric Crypto**
   - AES-CBC wrapper compatibility
   - Fernet-style envelope (AES/HMAC compat wrapper)

5. **FIPS Build Profile**
   - Go 1.24 `GOFIPS140` module configuration
   - Multi-arch FIPS build validation (`x86_64`, `aarch64`, `ppc64le`, `s390x`)
   - CRAM-MD5 handling strategy for SMTP edge cases
   - MD5 restriction enforcement in Go equivalent
   - FIPS mode startup smoke test in CI for each architecture

6. **TLS Termination and Cipher Policy**
   - Termination model decision: keep nginx through M4 (recommended) vs Go-native TLS
   - Transitional minimum: TLS 1.2 + TLS 1.3
   - Long-term target: TLS 1.3-preferred with explicit legacy exception list
   - Preserve proxy protocol behavior
   - Preserve HSTS and security-header behavior
   - Port/protocol mapping validation

7. **Cross-Runtime Crypto Test Matrix**
   - Python-encrypted → Go-decrypted fixture tests
   - Go-encrypted → Python-decrypted backward tests
   - Schema1 manifest sign/verify cross-runtime tests
   - FIPS mode startup and smoke tests per architecture
   - Negative tests for disallowed algorithms under `fips-strict`

### Acceptance Criteria
- AES-CCM library selected, FIPS-vetted, and approved
- All 13 crypto areas mapped to Go implementations with FIPS compatibility verified
- `convert_secret_key` test vectors pass for all 3 input modes
- Cross-runtime encryption/signing tests pass in FIPS-on and FIPS-off
- TLS termination model decision made and documented
- TLS handshake compatibility tests pass for supported clients
- SHA1-signing policy decision made for CloudFront/Swift under FIPS-strict
- FIPS smoke tests pass on all 4 architectures
- Security regression checklist integrated into cutover go/no-go

### Dependencies
- Feature 1 (Go Module Bootstrap)

### Plan References
- `plans/rewrite/fips_crypto_migration.md`
- `plans/rewrite/tls_security_posture.md`

---

## Feature 13: Storage Backend Migration

**Summary:** Migrate all 13 storage drivers and the distributed storage routing layer from Python to Go, preserving chunked upload semantics, signed URL behavior, and CDN compatibility.

**Business Value:** Storage is Quay's most operationally critical subsystem. Incorrect behavior causes data loss, replication failures, or CDN serving errors across customer-facing production registries.

**Milestone:** M2 (registry requires storage), cross-cutting
**Gates:** G10 (Storage Backend Migration)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Go Storage Interface**
   - Define single Go storage interface for blob, manifest, and chunk operations
   - Error normalization across backends
   - Chunked upload semantics preserved

2. **S3-Compatible Driver Family (Priority)**
   - `S3Storage`
   - `RHOCSStorage`
   - `IBMCloudStorage`
   - `STSS3Storage`
   - `RadosGWStorage`
   - Maximize code reuse across S3-compatible backends

3. **CDN-Backed Drivers**
   - `CloudFrontedS3Storage` — RSA PKCS1v15 + SHA1 signed URLs
   - `CloudFlareS3Storage` — RSA PKCS1v15 + SHA256 signed URLs
   - `AkamaiS3Storage` — HMAC EdgeAuth token
   - `MultiCDNStorage`
   - Signed URL compatibility validated via fixtures

4. **Other Drivers**
   - `GoogleCloudStorage`
   - `SwiftStorage`
   - `AzureStorage`
   - `LocalStorage` (required for mirror mode)

5. **Distributed Storage Routing**
   - `DistributedStorage` multi-location routing semantics preserved
   - Placement invariants unchanged (unless explicitly approved)
   - Storage location selection and fallback behavior

6. **Download Proxy**
   - `/_storage_proxy_auth` flow preserved
   - JWT validation endpoint semantics

7. **Storage Contract Tests**
   - Driver-specific contract tests (Python vs Go)
   - Mixed-runtime upload/download/read-after-write tests
   - Chunk resumability tests for interrupted uploads
   - Signed URL compatibility tests per CDN driver
   - Migration tracker: every row has owner, status, parity test ID

### Acceptance Criteria
- All 13 storage drivers tracked in `storage_driver_migration_tracker.csv` with status
- S3-compatible family passes parity tests
- CDN signed URL behavior matches Python for all 3 CDN drivers
- DistributedStorage routing parity verified
- Download proxy parity verified
- No cutover without passing driver-specific contract tests
- Repo mirror path uses Go-native `containers/image` (D-005 approved)

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 12 (Cryptography/FIPS) — CDN signing algorithms

### Plan References
- `plans/rewrite/storage_backend_inventory.md`
- `plans/rewrite/generated/storage_driver_migration_tracker.csv`

---

## Feature 14: Redis Usage and Runtime Support Component Migration

**Summary:** Migrate all 9 Redis usage patterns and 8 runtime support components from Python to Go, preserving Lua script atomicity, pub/sub semantics, distributed lock behavior, and in-process side effects.

**Business Value:** Redis patterns power real-time features (build logs, user events), pull metrics, caching, and distributed coordination. Runtime support components handle metrics, analytics, and file serving. Behavioral drift breaks production observability and coordination.

**Milestone:** M3-M4 (as consumers are migrated)
**Workstreams:** WS10 (Runtime Support Components and Redis Patterns)
**Gates:** G5 (Runtime Components), G12 (Redis Migration)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Redis Client Foundation**
   - Go client: `go-redis` (single, sentinel, cluster support)
   - Lua scripts checked in as explicit assets with SHA pinning
   - Key schema: preserve existing prefixes and key composition

2. **Redis Pattern Migration (9 patterns)**
   - Build logs — lists, key TTL, log ordering and retention
   - User events — pub/sub fanout timing, delivery loss handling
   - Pull metrics — Lua + hash counters, script atomicity, key naming
   - Data model cache — get/set with cluster support, stampede/fallback behavior
   - Distributed locks — lock keys/leases, lease expiry, re-entrancy
   - Build orchestration — keyspace notifications, coordination keys, event ordering
   - Pull metrics flush worker — SCAN/RENAME/HGETALL/DELETE atomic key-claim + retry on DB failure
   - Read/write split cache client — separate read + write clients, replica lag/staleness
   - Redis health checks — ping/set/get for deployment readiness

3. **Redis Migration Rules**
   - No key naming changes in mixed mode without dual-read/dual-write plan
   - Preserve Lua script atomicity for pull metrics
   - Preserve lock TTL defaults and lock-loss behavior
   - Preserve pub/sub channels and payload schemas
   - Replace production `KEYS` usage with `SCAN` before Go cutover
   - Keep explicit fallback behavior when Redis is degraded

4. **Runtime Support Component Migration (8 components)**
   - `PrometheusPlugin` — background push thread and request metrics
   - `Analytics` — optional Mixpanel queue + sender thread
   - `UserEventsBuilderModule` — realtime pub/sub semantics, heartbeat
   - `PullMetricsBuilderModule` — async pull tracking + Redis script + thread pool
   - `BuildCanceller` — build cancel orchestration from API paths
   - `Userfiles` — app-level route registration + file serving/upload
   - `DownloadProxy` — storage proxy JWT validation endpoint
   - `MarketplaceUserApi` / `MarketplaceSubscriptionApi` — external entitlement lookup

5. **Redis and Runtime Test Suites**
   - Mixed producer/consumer tests for each Redis pattern
   - Lua behavior parity tests using recorded inputs/outputs
   - Lock-contention and lock-expiry tests
   - Redis-failure chaos tests (timeouts, reconnects, failover)
   - Pullstats flush tests covering orphaned `:processing:` keys and DB-failure retries
   - Runtime component thread/pool side-effect test cases

### Acceptance Criteria
- All 9 Redis patterns mapped to Go code owners with parity tests
- Lua script parity tests green
- Orchestrator/keyspace notification behavior validated in staging
- Pullstats flush worker SCAN/RENAME/DELETE lifecycle validated
- Redis lock-path and health-check behavior documented
- All 8 runtime support components mapped (parity or approved retirement)
- Per-pattern error and latency dashboards available

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 10 (Data Access Layer) — pullstats flush writes to DB

### Plan References
- `plans/rewrite/redis_usage_inventory.md`
- `plans/rewrite/runtime_support_components.md`
- `plans/rewrite/runtime_component_execution_plan.md`
- `plans/rewrite/generated/runtime_component_mapping.csv`

---

## Feature 15: Deployment Architecture, Container Image Strategy, and Config-Tool Evolution

**Summary:** Define and implement deployment topology for Go services (Kubernetes + VM), evolve container images from Python-heavy to Go-first, and update the config-tool to validate rewrite-era configuration.

**Business Value:** Deployment architecture determines how Go services run alongside Python during migration and standalone post-migration. Container image modernization reduces CVE surface, image size, and operational complexity. Config-tool validation prevents misconfiguration in hybrid deployments.

**Milestone:** M1-M5 (progressive)
**Workstreams:** WS11 (Deployment and Image Modernization)
**Gates:** G13 (Deployment/Image/Config/TLS)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Binary and Process Model**
   - Single Go binary with subcommands: `quay serve`, `quay worker`, `quay admin`
   - Shared config and observability stack
   - Systemd-managed processes for VM deployments
   - Unified readiness/liveness endpoints for all Go services

2. **Kubernetes Deployment**
   - Dedicated Deployments for `api-service` and `registryd`
   - Separate worker Deployments per worker family
   - Horizontal autoscaling based on queue lag and request latency
   - Config-provider distribution for switch ownership state
   - Quay Operator manages routing between Python and Go services

3. **VM / Standalone Deployment**
   - Systemd-managed processes for api-service, registryd, and workers
   - Optional all-in-one compatibility profile for transitional installs
   - Explicit health probes and restart policies per process
   - Process supervision equivalence with legacy supervisord

4. **Container Image Evolution**
   - M0-M1: Current Python image + Go sidecar/service images for canary
   - M2-M3: Hybrid — registryd/api-service Go images + reduced Python fallback
   - M4: Worker-specific Go images; Python workers only where incomplete
   - M5: Go-first production images; Python emergency-only fallback
   - Component elimination: supervisord → explicit orchestration, nginx → pending decision, memcached/dnsmasq → retain only if required, skopeo → Go-native `containers/image` (D-005)
   - Multi-arch builds: `x86_64`, `aarch64`, `ppc64le`, `s390x`
   - Per-arch build validated before M2; FIPS smoke pass required
   - Image-size trend tracking with regression alerts
   - CVE and base-image policy checks in CI

5. **Config-Tool Co-Evolution**
   - Validate owner-switch keys from `switch_spec.md`
   - Validate transport settings from `switch_transport_design.md`
   - Validate new service blocks for `registryd`, `api-service`, and Go workers
   - Add compatibility warnings for deprecated Python-only settings
   - Config fixtures for hybrid and go-only deployments
   - CI checks for schema revisions
   - Migration notes for operators using existing config templates

6. **Reference Deployment Manifests**
   - K8s manifests/templates for hybrid and Go-only topologies
   - VM deployment scripts for standalone and HA profiles
   - Rollback script/runbook for owner-switch fallback to Python services

### Acceptance Criteria
- Reference deployment manifests for K8s and VM documented and tested
- First canary environment runs on planned deployment model
- Process supervision equivalence with legacy supervisord proven
- Per-milestone image BOM documented and signed off
- Config-tool validates all rewrite-required settings without undocumented fields
- Multi-arch and FIPS build matrix validated
- Image-size regression alerts operational

### Dependencies
- Feature 1 (Go Module Bootstrap)
- Feature 3 (Switch Control Plane) — config validation for switches

### Plan References
- `plans/rewrite/deployment_architecture.md`
- `plans/rewrite/image_strategy.md`
- `plans/rewrite/config_tool_evolution.md`
- `plans/rewrite/tls_security_posture.md`

---

## Feature 16: Operational Tooling Migration and Disposition

**Summary:** Triage all Python operational/admin scripts, assign disposition (port, retire, or maintain temporarily), and execute accordingly. Ensure no production runbook references unmapped tooling.

**Business Value:** Operational scripts support SRE workflows, credential management, data migration, and troubleshooting. Unmapped scripts create operational gaps during and after migration.

**Milestone:** M3-M5
**Workstreams:** Part of WS11
**Gates:** G7 (Operational Tooling)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Tooling Inventory and Disposition**
   - Every operational script assigned disposition per D-004 baseline:
     - `go-port-required` — supports production ops/SRE runbooks; must remain available
     - `retire-approved` — obsolete; removed with documented replacement
     - `python-compat-window` — Python-only temporarily with explicit sunset date
   - Priority buckets: `P-ops-high` (credential/key gen, replication/data-migration), `P-ops-medium` (invoicing/email/manual support), `P-ops-low` (one-off diagnostics)

2. **Go Port Implementation**
   - Port `go-port-required` scripts as `quay admin` subcommands
   - Define Go command path and compatibility tests
   - Validate input/output contract and side effects

3. **Retirement Execution**
   - Document replacement or no-op guidance for retired scripts
   - Add approval note and fallback runbook
   - Identify scripts used only during migration — reclassify to `python-compat-window`

4. **Transition Safety Validation**
   - No production runbook references unmapped Python-only script
   - Transition-period script validation (G7 currently requires this)

### Acceptance Criteria
- Every operational tooling inventory row has approved disposition
- No production runbook references unmapped Python-only script
- `go-port-required` scripts ported with compatibility tests
- Transition safety check complete: migration-only scripts correctly classified

### Dependencies
- Feature 1 (Go Module Bootstrap) — for Go ports

### Plan References
- `plans/rewrite/operational_tooling_plan.md`
- `plans/rewrite/generated/operational_tooling_inventory.md`
- `plans/rewrite/generated/operational_tooling_disposition.csv`

---

## Feature 17: Route Auth Verification Acceleration

**Summary:** Accelerate the verification of auth behavior for all 413 route rows through automated pre-verification and owner signoff promotion, reducing the manual backlog to a targeted exception set.

**Business Value:** Auth verification is a prerequisite for safe capability flips. Automated verification reduces manual review burden and accelerates M0 readiness.

**Milestone:** M0 (prerequisite)
**Workstreams:** WS12 (Route Auth Verification Acceleration)
**Gates:** G3 (Route/Worker Verification)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Automated Pre-Verification**
   - Run `route_auth_auto_verify.py` against codebase
   - Generate automated route auth verification report
   - Identify routes requiring manual review

2. **Manual Backlog Resolution**
   - Target: reduce `source-anchored-needs-review` rows to ≤ 50
   - Assign remaining rows via signoff waves
   - Close each row with owner signoff and test evidence

3. **Owner Signoff Promotion**
   - Promote all `verified-source-anchored` rows to `verified` with owner signoff
   - Update `route_auth_verification_checklist.csv` status
   - Current state: 413 rows at `verified-source-anchored`, 0 manual backlog

### Acceptance Criteria
- `source-anchored-needs-review` rows ≤ 50
- All route rows have auth mode classification with evidence
- Signoff wave schedule complete with named owners
- Automation script runs in CI to detect auth drift

### Dependencies
- None (can proceed independently)

### Plan References
- `plans/rewrite/route_auth_automation_plan.md`
- `plans/rewrite/scripts/route_auth_auto_verify.py`
- `plans/rewrite/generated/route_auth_verification.md`
- `plans/rewrite/generated/route_auth_verification_checklist.csv`
- `plans/rewrite/generated/route_auth_review_waves.md`

---

## Feature 18: Python Deactivation and Unified Go Deployment

**Summary:** Complete the migration by deactivating all Python endpoints and workers, removing Python from the default deployment topology, and establishing the Go binary as the sole production runtime.

**Business Value:** Eliminates dual-runtime operational complexity, reduces CVE surface, enables Go-native performance and deployment models, and completes the strategic objective of the rewrite.

**Milestone:** M5 (Python Deactivation and Deployment Unification)
**Labels:** rewrite
**Component:** quay

### Scope / Suggested Epics

1. **Full Cutover Validation**
   - Cutover matrix shows all capabilities owned by Go
   - Every route/worker/queue/runtime tracker row status = `go` or `retired-approved`
   - All quality gates pass: contract parity, performance budgets, security, FIPS, observability

2. **Python Runtime Deactivation**
   - Python endpoints disabled in steady state
   - Python workers disabled in steady state
   - Python retained as emergency-only fallback for bounded period
   - Explicit timeline and criteria for complete Python removal

3. **Deployment Topology Unification**
   - nginx removed from default deployment topology (Go serves directly)
   - `quay serve` is the container entrypoint for all deployment profiles
   - `quay install` profiles (`standalone`, `ha`) generate Quadlet deployments using Go-only container images

4. **Mirror-Registry Unification**
   - `quay` CLI unifies `mirror-registry`, `quay-distribution-main`, and `config-tool` into single binary
   - Mirror-registry deployment uses Go binary directly (no Ansible/EE)

5. **Legacy Component Removal**
   - supervisord removed
   - memcached/dnsmasq removed (if not required)
   - skopeo replaced by Go-native `containers/image`
   - `sqlalchemybridge.py` retired (permitted after M5 per db_migration_policy.md §10.7)
   - `QUAY_OVERRIDE_SERVICES` phased out for migration-scoped capabilities

6. **Post-Migration Operational Validation**
   - Production stability under Go-only runtime confirmed
   - Emergency rollback to Python exercised one final time
   - Python fallback sunset timeline executed
   - Final deployment topology documented and validated

### Acceptance Criteria
- Cutover matrix: 100% capabilities owned by Go
- Go-only container images in production for all deployment profiles
- nginx removed from default topology
- `quay serve` serves all deployment profiles
- Python emergency fallback available for bounded sunset period
- No production dependency on Python runtime
- Legacy components (supervisord, skopeo, bridge) removed

### Dependencies
- All Features 1-17 (this is the culmination of the entire rewrite)

### Plan References
- `plans/rewrite/quay_rewrite.md` §6 (M5 exit criteria)
- `plans/rewrite/cutover_matrix.md`
- `plans/rewrite/deployment_architecture.md`
- `plans/rewrite/image_strategy.md`
