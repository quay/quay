# Quay Rewrite Plan (Python → Go): Strangler + Rearchitecture, TDD-first

> **Scope:** Backend only. Preserve existing APIs and externally observable behavior.
>
> **Constraints (non-negotiable):**
> - Quay powers quay.io at scale; treat DB schema and object storage as critical invariants.
> - Not a 1:1 port: retain functionality, not legacy patterns.
> - Test-Driven Development always (unit + integration + contract + E2E). Target **>=95% coverage** for new Go code.
> - **All API surfaces are strictly contractual** (paths, methods, headers, status codes, payload shapes, pagination, error formats).
> - Do not break existing API contracts (`/v2/*` and Quay REST APIs). Backward compatibility is mandatory.
> - No frontend rewrites; rely on existing React UI and Playwright tests.
> - **No Go web framework**: use `net/http` + stdlib `http.ServeMux` (Go 1.22+ patterns) + small internal middleware.
> - Cloud-native architecture, but must also run standalone on a VM (Podman quadlets/systemd acceptable).
> - Must accommodate future security features (SHA512, TLS 1.3) without destabilizing storage/DB.
> - Mirror Registry’s disconnected install flow must remain viable (it can evolve to bundle multiple images).

## How to use this plan

- **Maintainers** answer the questions in **Discovery questions** and decide milestone ordering.
- **Agents (or humans)** implement one “PR-sized task” at a time, always starting with a failing test.
- Every milestone has:
  - a definition of done
  - explicit code locations
  - test strategy (unit/integration/contract/e2e)
  - rollout and rollback procedures

## Table of contents

1. Discovery questions
2. North-star architecture
3. Migration strategy (strangler)
4. Go codebase layout and standards
5. Testing strategy (TDD + contract + E2E)
6. Performance/scaling guardrails (DB + object store)
7. Workers and cloud-native rework
8. Registry (/v2) via Distribution fork + schema v1 compatibility
9. Security roadmap (SHA512, TLS 1.3, crypto agility)
10. Packaging: Kubernetes, VM (quadlets), Mirror Registry, image size
11. Team execution plan (4 people) + workstreams
12. Appendix: templates, example code, example tests

---

## 1. Discovery questions (please answer before implementation)

These are intentionally detailed; they bound the design and prevent expensive rewrites.

### 1.1 Production behavior and invariants

1. **Traffic profile**
   - Peak RPS on `/v2/*` vs Quay REST API endpoints?
   - Peak concurrent uploads? Typical blob sizes? Layer size distribution?
   - % of traffic that is anonymous pulls vs authenticated?
   - Known hot endpoints (DB-heavy) besides registry pushes/pulls?

2. **Client compatibility**
   - Do you still need to support:
     - Docker clients older than 19.x?
     - Schema v1 pull? Schema v1 push?
     - Any nonstandard quay.io client behaviors?
   - Which auth flows must remain identical (basic auth, bearer token, OAuth, robot tokens, OIDC, LDAP, etc.)?

3. **Data invariants (must not change without explicit migrations)**
   - Confirm primary DB: Postgres? Supported versions?
   - Multiple datastores (Postgres + Redis + …)?
   - Which tables/object key prefixes are treated as stable public contract (mirror tooling, migrations, etc.)?
   - Existing cross-region replication patterns?

4. **Object storage invariants**
   - Which backends are supported today (S3, GCS, Swift, local, Azure, …)?
   - Are object keys strictly stable? (They likely must remain stable to avoid reuploading.)
   - Any multi-region storage replication or read-preference behaviors currently deployed?

5. **Operational constraints**
   - SLOs and error budgets? p99 latency targets? availability?
   - Required observability: Prometheus metrics? tracing? audit logs?
   - Hard constraints on memory/CPU per component?

6. **Known pain points**
   - Besides Peewee connection explosion, what are the top 5 incidents/root causes in the last year?
   - Which workers are flaky or hardest to operate?
   - Which APIs are most brittle and should not be touched early?

### 1.2 Feature scope and decomposition

7. **Feature boundaries**
   - Which features are required for “registry-only” deployments (OpenShift Image Registry replacement path)?
   - Which features are required for “full Quay” deployments?
   - Which features can be explicitly out of scope for v1 of the Go services (but still served by Python during transition)?

8. **Workers and background jobs**
   - List current worker types (GC, mirroring, notifications, scanning orchestration, build manager, indexing, …) and their triggers.
   - What queue technology is currently used (Redis, Postgres, custom, …)?
   - Any workers require strong ordering or exactly-once semantics?

9. **Config + deployment**
   - How is configuration consumed today (config bundle, env vars, config app)?
   - Must “config mode” remain as-is? Or can it be redesigned while keeping compatibility with generated bundles?

10. **Security roadmap**
    - SHA512: dual-hash support (sha256 + sha512) or migrate to sha512 as default?
    - TLS 1.3: where is TLS terminated in typical deployments (ingress, nginx, load balancer, in-container)?
    - Post-quantum: what does “safe” mean for your threat model (hash agility, signature agility, PQ TLS readiness, etc.)?

### 1.3 Delivery constraints

11. **Rollout strategy**
    - Shadow traffic is not feasible at quay.io scale; plan uses tenant-scoped canaries instead.
    - Are canaries allowed per endpoint/path? Are feature flags acceptable?
    - Do you require zero-downtime releases?

12. **Team constraints**
    - Any hard deadlines? If yes, which features must land first?
    - Skill distribution: who owns registry protocol work vs platform/infra vs DB/storage vs workers?

13. **Legal/compatibility**
    - Any contractual obligations on API response shapes (including error messages)?
    - Any compliance requirements (FIPS mode, audit log retention, etc.)?

> **Output requested from maintainers:** a short `plans/answers.md` capturing these decisions. Agents should treat it as authoritative.

### 1.4 Maintainer answers captured so far (2026-02-08)

- **API contract:** all API surfaces are strictly contractual; do not break anything.
- **Auth:** current auth is clumsy (multiple forms). You want modernization (especially apps + robot tokens), but **all existing flows must continue to work**. You’re open to future deprecation (e.g., OAuth apps) but not removal in this migration.
- **quay.io storage stack:** Postgres (with read replicas), Redis, and S3 are the production stack for quay.io.
- **Object storage invariant:** **object keys must not change**.
- **DB pain points:** excessive connections (likely Peewee) and long queries are the primary pain points; reads are not consistently sent to read replicas today.
- **Regions:** currently primary region is read/write; secondary region is read-only (used during failover).
- **Future direction:** eventual multi-region read/write is a desired direction (e.g., Aurora/global DB patterns), but not a near-term requirement.
- **Queue semantics:** unknown/uncertain; the plan must discover current queue tech and semantics from the code and preserve required behavior.
- **TLS:** typically terminated at a load balancer in front of Quay; further hardening is desired for post-quantum readiness.
- **FIPS:** must-have; current deployments require it.
- **Rollout:** no traffic shadowing (too costly). Use **path-based routing** and small-scale canaries by **subset of organizations/repositories**, controlled by trusted feature flags.
- **Workers:** there are many workers; most are critical and must be accounted for in the new design.
- **Packaging/UX:** multiple images are acceptable, but you must still provide a “single application” run experience. Registry-only focuses on push/pull/auth, with a clean extension path.


---

## 2. North-star architecture

### 2.1 Design principles

1. **Strangler fig migration**: introduce new Go components behind routing + feature flags; keep Python as fallback.
2. **Contract-first APIs**: every migrated endpoint ships with contract tests proving parity with legacy behavior.
3. **API surfaces are contracts**: paths/methods/headers/status/payloads/pagination/errors are treated as immutable without an explicit deprecation plan.
4. **DB + object store are contracts**: no schema changes, and **object keys must not change**, unless explicitly designed, reviewed, and migration-tested.
5. **No Go web framework**: use `net/http` + stdlib `http.ServeMux` (Go 1.22+ patterns) + internal middleware.
6. **Cloud-native by default, single-app UX supported**: split services/workers for Kubernetes; provide a VM “single application” experience via quadlets/podman kube.
7. **Canary rollout without shadow traffic**: use path-based routing + org/repo allowlists + feature flags; no full traffic mirroring/shadowing.
8. **Security + crypto agility**: SHA512 support, TLS 1.3 readiness, and **FIPS compliance** are first-class requirements.

### 2.2 Components

| Component | Type | Primary responsibility | Notes |
|---|---|---|---|
| **edge-router** | Go service or ingress/gateway config | Path-based routing, auth passthrough, request IDs, rate limiting hooks | Enables strangler rollout; can be optional if ingress supports routing |
| **registryd** (Distribution fork) | Go service | Implements `/v2/*` (push/pull, manifests, blobs) | Add schema v1 compatibility layer; integrate Quay auth + storage |
| **core-api** | Go service | Quay REST APIs (users/orgs/repos, tags, perms) | Generated OpenAPI stubs where possible |
| **authn/authz** | Go lib + optional service | Token issuance, robot tokens, session validation | Start as a library embedded in services, optionally split later |
| **metadata** | Go library | Data access layer for Postgres | Use `pgx` + `sqlc`; strict pooling |
| **storage** | Go library | Object storage abstraction (S3/GCS/Swift/local) | Must preserve object key structure and semantics |
| **workers** | Go binaries | GC, mirroring, notifications, scanning orchestration, indexing | Run as Deployments/CronJobs; VM uses quadlets |
| **config-tool** | Optional Go tool/service | Generate config bundles & validate config | Keep bundle format stable |

### 2.3 Deployment profiles

We explicitly support two profiles:

1. **Full Quay** (quay.io-equivalent): registry + UI/API + builds + mirroring + notifications + scanning integrations.
2. **Registry-only** (OpenShift Image Registry replacement path): `/v2` + auth + minimal metadata; optional UI.

Both profiles must be deployable:
- **On Kubernetes**: multiple Deployments/CronJobs, HPA, PodDisruptionBudgets.
- **On a VM**: multiple containers orchestrated by **Podman quadlets** (systemd).

### 2.4 Routing model (strangler)

- **Phase A (parity)**: All traffic still served by Python, but routed through a stable edge (ingress/nginx/edge-router).
- **Phase B (partial)**: `/v2/*` routed to `registryd`, everything else to Python.
- **Phase C (incremental)**: selected REST endpoints routed to `core-api`.
- **Phase D (complete)**: all paths routed to Go services; Python kept only as emergency fallback until removed.

---

## 3. Migration strategy (strangler): milestones and PR-sized tasks

This section is written to be executed by multiple people (and agentic AI) in parallel.

### 3.1 Milestone 0 — Baseline: freeze contracts + build harness

**Goal:** lock down current behavior so new Go code can be verified continuously.

**Definition of done:**
- A reproducible local harness can start:
  - the legacy Python Quay service
  - the new Go components (even if they proxy back to legacy)
  - shared dependencies (Postgres, Redis, object store emulator)
- A contract test suite can replay a set of API calls against both legacy and Go and compare results.

**PR-sized tasks:**
1. Create a new top-level directory for Go code:

```
go/
  cmd/
    edge-router/
    registryd/
    core-api/
  internal/
    config/
    httpx/
    auth/
    metadata/
    storage/
    observability/
    contract/
```

2. Add `go.mod` pinned to a single toolchain version and a basic CI job:

```bash
go test ./... -count=1
```

3. Add a `compose/rewrite` docker-compose profile that starts:
- `quay-legacy` (existing image)
- `edge-router` (Go)
- `postgres` (existing config)
- `redis` (existing config)
- `minio` (or your current local object store equivalent)

4. Add a contract test runner (Go) that:
- loads HTTP request fixtures (YAML/JSON)
- sends each request to legacy and Go endpoints
- normalizes response bodies/headers
- asserts parity

Example fixture:

```yaml
- name: list_repos
  method: GET
  path: /api/v1/repository
  headers:
    Authorization: Bearer ${TOKEN}
  expect:
    status: 200
    jsonSchema: schemas/list_repos.json
```

5. Add a performance baseline suite:
- pick 5 high-impact endpoints
- use k6/vegeta to capture latency/throughput on a local dataset
- store results as CI artifacts for regression detection

### 3.2 Milestone 1 — Edge router: stable ingress and path-based routing

**Goal:** establish the routing layer that enables gradual cutover.

**Definition of done:**
- `edge-router` proxies all requests to legacy by default.
- Supports a config map like:

```yaml
routes:
  - pathPrefix: /v2/
    upstream: http://registryd:5000
    enabled: false
  - pathPrefix: /api/
    upstream: http://core-api:8081
    enabled: false
  - pathPrefix: /
    upstream: http://legacy:8080
    enabled: true
```

**Implementation notes:**
- Use `net/http` + `httputil.ReverseProxy`.
- Preserve headers and status codes exactly.
- Add structured logging + request ID propagation.

### 3.3 Milestone 2 — Fork Distribution and land `registryd` for `/v2/*`

**Goal:** replace Quay’s `/v2` implementation with a fork of `distribution/distribution`, while keeping all behaviors Quay depends on.

**Definition of done:**
- `/v2/_catalog`, pull, push, blob upload/download, manifest upload/download work against existing DB + object storage.
- Docker schema v1 compatibility matches current Quay behavior (pull and, if required, push).
- No DB schema changes.

**Key integration points:**
1. Auth: token issuance and `WWW-Authenticate` flow compatible with Quay.
2. Storage driver: maps to existing object keys/layout.
3. Metadata: tags/manifests map to existing tables.

**Rollout plan:**
- Route `/v2/*` to `registryd` behind a feature flag.
- Canary by namespace/tenant if possible.
- Keep ability to flip routing back to Python immediately.

### 3.4 Milestone 3 — Core REST API service (`core-api`) in Go (read-only first)

**Goal:** start migrating Quay REST APIs incrementally.

Order of migration:
1. Read-only endpoints with minimal side effects.
2. Auth/session/token endpoints.
3. Write endpoints that modify metadata (repos/tags/perms), one resource at a time.

**Definition of done:**
- Contract tests pass for migrated endpoints.
- Playwright passes on the React UI against edge-router.

### 3.5 Milestone 4 — Core REST API write paths + strong invariants

**Goal:** move write paths with explicit transaction semantics and safety checks.

**Definition of done:**
- Writes use `sqlc`-generated queries, explicit transactions, and idempotency where required.
- Avoid dual-writes; prefer single-writer cutovers behind feature flags and canary tenants.

### 3.6 Milestone 5 — Workers and background jobs: decompose and replace supervisor

**Goal:** replace monolithic “supervisor runs everything” with cloud-native workloads.

**Definition of done:**
- Each worker is its own Go binary and container image.
- Kubernetes: Deployments (queue-driven) or CronJobs (scheduled).
- VM: Podman quadlets start each worker container.

### 3.7 Milestone 6 — Remove Python monolith from the critical path

**Goal:** legacy Python serves zero traffic in steady state.

**Definition of done:**
- Edge-router routes all paths to Go services.
- Legacy remains only as emergency fallback until removed.
- Python removed from default deployment profile.

---

## 4. Go codebase layout and standards (agent-friendly)

### 4.1 Layout and naming

- `go/cmd/<service>/main.go` — minimal bootstrap
- `go/internal/<area>` — private application code
- `go/pkg/<name>` — exported only if needed externally

Suggested package boundaries:
- `internal/httpx`: HTTP middleware, error mapping, response helpers
- `internal/config`: load config from env/files, validate, defaults
- `internal/observability`: logging, metrics, tracing
- `internal/metadata`: DB access (pgx/sqlc), repositories
- `internal/storage`: object storage abstraction
- `internal/auth`: token issuance, authz decisions
- `internal/contract`: contract test runner utilities

### 4.2 Dependency choices (default)

- HTTP: `net/http` + stdlib `http.ServeMux` (Go 1.22+ patterns). No external web frameworks.
- DB: `pgx/v5` + `pgxpool`
- Query gen: `sqlc`
- Config: `envconfig` or minimal custom loader
- Observability: OpenTelemetry + Prometheus client
- Testing: `testing`, `testify`, `testcontainers-go`

### 4.3 Error mapping

Implement a single error mapping layer so behavior remains stable:

```go
type APIError struct {
  Code string `json:"error_code"`
  Message string `json:"message"`
}

func WriteError(w http.ResponseWriter, status int, code, msg string) {
  w.Header().Set("Content-Type", "application/json")
  w.WriteHeader(status)
  _ = json.NewEncoder(w).Encode(APIError{Code: code, Message: msg})
}
```

Contract tests should assert exact status codes and error payloads for known errors.

### 4.4 DB connection pooling + read replica routing (fix Peewee-era pathologies)

**Rules:**
- No per-request pools. Each service has:
  - **one writer pool** (required)
  - **one reader pool** (optional; defaults to writer) for read replicas
- Every query must be **context-bound** and **instrumented** (timing + rows + error).
- “Read your writes” correctness beats replica offload: if a request wrote, subsequent reads in that request must use the writer.

```go
type DB struct {
  RW *pgxpool.Pool // writer / primary
  RO *pgxpool.Pool // read replicas (optional)
}

type Role int
const (
  RoleRW Role = iota
  RoleRO
)

func NewDB(ctx context.Context, rwDSN string, roDSN string, maxConns int32) (*DB, error) {
  mk := func(dsn string) (*pgxpool.Pool, error) {
    cfg, err := pgxpool.ParseConfig(dsn)
    if err != nil { return nil, err }
    cfg.MaxConns = maxConns
    cfg.MinConns = 1
    cfg.MaxConnIdleTime = 2 * time.Minute
    cfg.HealthCheckPeriod = 30 * time.Second
    return pgxpool.NewWithConfig(ctx, cfg)
  }

  rw, err := mk(rwDSN)
  if err != nil { return nil, err }

  db := &DB{RW: rw, RO: rw}
  if roDSN != "" {
    ro, err := mk(roDSN)
    if err != nil { return nil, err }
    db.RO = ro
  }
  return db, nil
}

func (db *DB) Pool(role Role) *pgxpool.Pool {
  if role == RoleRO { return db.RO }
  return db.RW
}
```

**Enforcement pattern (agent-friendly):**
- HTTP middleware sets a default role for the request:
  - `GET/HEAD` → `RoleRO` (unless explicitly overridden)
  - `POST/PUT/PATCH/DELETE` → `RoleRW`
- A write sets `ctx = WithForceRW(ctx)` so later reads use writer.

```go
type ctxKey string
const (
  ctxDBRole    ctxKey = "dbRole"
  ctxForceRW   ctxKey = "forceRW"
)

func WithDBRole(ctx context.Context, r Role) context.Context { return context.WithValue(ctx, ctxDBRole, r) }
func DBRole(ctx context.Context) Role {
  if ctx.Value(ctxForceRW) == true { return RoleRW }
  if v, ok := ctx.Value(ctxDBRole).(Role); ok { return v }
  return RoleRW
}
func WithForceRW(ctx context.Context) context.Context { return context.WithValue(ctx, ctxForceRW, true) }
```

**Testing requirement (non-negotiable):**
- Integration regression test that:
  1. Executes representative endpoints.
  2. Asserts **no connection leaks** (via `pg_stat_activity` delta).
  3. Asserts **read queries route to RO** when safe (via `application_name` tagging per pool, or separate DB users).
- Add query budget tests for known hot endpoints (max rows scanned / max duration) to catch “long query” regressions early.

---

## 5. Testing strategy (TDD + contract + E2E)

### 5.1 Test pyramid and mapping

1. **Unit tests**: pure logic (auth decisions, schema conversion, request parsing).
2. **Integration tests**: Postgres + MinIO (testcontainers) verifying storage/DB behaviors and pooling.
3. **Contract tests**: parity vs legacy per endpoint migrated.
4. **E2E tests**: reuse React UI Playwright tests against edge-router.
5. **Load tests**: k6/vegeta scripts for `/v2` plus 3–5 heavy REST endpoints.

### 5.2 TDD workflow (for agentic AI)

For every new behavior:
1. Write failing unit or contract test.
2. Implement minimal code to pass.
3. Refactor.
4. Run relevant suites.

Suggested Make targets:

```bash
make go-test
make go-integration-test
make contract-test
make playwright
```

### 5.3 Contract test guidance

Compare:
- status code
- selected headers (`Content-Type`, auth challenges, distribution headers)
- JSON body shape and values
- error messages where clients depend on them

Ignore only:
- `Date`, `Server`, request IDs
- ordering of JSON keys

### 5.4 Example: integration test with MinIO (placeholder)

Use testcontainers to boot MinIO, then exercise `storage.PutBlob/GetBlob`. (Implementation depends on Quay’s storage key scheme.)

---

## 6. Performance and scaling guardrails (DB + object store)

### 6.1 DB connections

Rules:
- `pgxpool` with explicit `MaxConns` and timeouts.
- All queries use `context` deadlines.
- Avoid N+1 queries; use batched queries and explicit joins.

### 6.2 Object store IO

Rules:
- Streaming uploads/downloads; avoid buffering entire blobs.
- Avoid head/list calls in hot paths; cache metadata if safe.
- Use ETags and conditional requests where applicable.

### 6.3 Safe rollout (no shadow traffic)

**Constraint:** do not rely on shadow/mirror traffic; it’s too costly at quay.io scale.

Recommended rollout mechanics:
- **Path-based routing** via edge-router/ingress (e.g., route `/v2/*` to Go registry first).
- **Tenant-scoped canaries** (subset of orgs/repos) via a trusted feature-flag/allowlist.
  - Registry: parse `<org>/<repo>` from `/v2/<name>/...` and decide legacy vs Go.
  - REST: decide based on authenticated principal’s org (or explicit header/claim), then route.
- **Hard rollback**: routing flips back to legacy instantly.

Agentic implementation guidance:
- Edge-router supports a rule type like:
  - `canary.registry.allowRepos: ["orgA/repo1", "orgB/*"]`
  - `canary.api.allowOrgs: ["orgA", "orgB"]`
  - `defaultUpstream: legacy`
- Add contract tests for routing decisions (pure function tests) and end-to-end smoke tests for a canary repo.

---

## 7. Workers and cloud-native rework

### 7.1 Inventory

Maintainers fill this table:
### 7.1 Inventory and discovery (must be exhaustive)

**Goal:** produce an authoritative catalog of all background work and its semantics. Most workers are critical and must be preserved.

**Deliverable:** `plans/workers_inventory.md` with:
- every worker process (including “random” ones historically launched via supervisor)
- trigger type (queue / schedule / API event / DB polling)
- queue backend and semantics (at-least-once, ordering, dedupe keys, retry policy)
- side effects (DB writes, object deletes, external calls)
- idempotency strategy (required for safe retries)
- SLOs (latency, throughput) and concurrency limits

**Agentic repo-examination checklist (run in a dev checkout):**
1. Locate process definitions:
   - supervisor config, entrypoint scripts, Kubernetes manifests, operator templates.
2. Identify worker modules/binaries:
   - search for `worker`, `celery`, `rq`, `kombu`, `task`, `queue`, `scheduler`, `cron`, `gc`, `mirror`, `build`, `notification`, `security`, `scan`.
3. For each worker:
   - find the “main loop” and the enqueue/dispatch code paths
   - record the queue name/topic and payload schema (JSON fields)
   - record retry/backoff and dead-letter behavior
4. Write **contract tests** for queue payload schemas:
   - capture real payload examples from logs or staging
   - validate with JSON schema in tests

> This inventory milestone is a gate: do not delete/replace workers until they’re modeled and tested.


| Worker | Trigger | Inputs | Side effects | Required ordering | Can be CronJob? |
|---|---|---|---|---|---|
| garbage_collection | schedule | DB + storage | deletes blobs | yes/no | yes |
| repo_mirror | queue/schedule | remote registry creds | writes manifests/blobs | per-repo | maybe |
| notification_dispatch | queue | events | external calls | no | no |

### 7.2 Standard worker template

All workers share:
- config loader
- structured logging
- metrics endpoint
- health endpoint

### 7.3 Kubernetes pattern

- Queue workers: Deployment + HPA/KEDA
- Scheduled workers: CronJob

### 7.4 VM pattern (quadlets)

One quadlet per worker container; allow enable/disable by profile.

---

## 8. Registry (/v2) via Distribution fork + schema v1 compatibility

### 8.1 Fork strategy

Create `github.com/quay/distribution` fork.

Rules:
- keep fork minimal; upstream rebases should remain possible
- Quay-specific behavior behind interfaces/adapters

### 8.2 Storage invariants

Do not change object keys or DB schema early. Implement adapters:
- Distribution blob store adapter -> Quay storage
- Manifest/tag metadata adapter -> Quay DB tables

### 8.3 SHA512 digests without storage explosion

**Goal:** allow referencing the same bytes by multiple digests without duplicating bytes.

Model:
1. Store bytes once under a canonical key (likely sha256).
2. Maintain `blob_digest_map` in Postgres mapping (algo,digest) -> canonical_digest.

```sql
CREATE TABLE IF NOT EXISTS blob_digest_map (
  algo TEXT NOT NULL,
  digest TEXT NOT NULL,
  canonical_digest TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (algo, digest)
);
```

Upload path:
- If client uses sha512, stream-compute sha256 and store canonical once.
- Insert mappings for sha512->sha256 and sha256->sha256.

Download path:
- Resolve requested digest via mapping and serve canonical bytes.

**Risk:** DB writes. Put behind feature flag; add integration tests; canary carefully.

### 8.4 Docker schema v1 support

Plan:
- Middleware parses/validates schema1 manifests.
- Maintainers decide whether schema1 pushes must be accepted.
- If schema1 push is required: validate and store schema1 metadata; optionally convert to schema2/OCI internally while serving schema1 to old clients.

Tests:
- golden fixtures for schema1 manifests
- compatibility matrix with real clients

---

## 9. Security roadmap (SHA512, TLS 1.3, crypto agility)

### 9.1 TLS 1.3 (edge-terminated today, hardened tomorrow)

**Current production reality:** TLS is typically terminated at the load balancer in front of Quay.

Recommended:
- Keep TLS termination at LB/ingress for quay.io-scale deployments.
- Add **internal service-to-service mTLS** as an optional hardening layer (especially for “post-quantum readiness” planning).
- Support TLS 1.3 directly in Go services for standalone/VM deployments and for test harnesses.

Example TLS config (standalone/VM mode):

```go
srv := &http.Server{
  Addr: ":8443",
  Handler: handler,
  TLSConfig: &tls.Config{
    MinVersion: tls.VersionTLS12,
    MaxVersion: tls.VersionTLS13,
  },
}
log.Fatal(srv.ListenAndServeTLS("/etc/quay/tls.crt", "/etc/quay/tls.key"))
```

### 9.2 Post-quantum readiness

Near-term actions:
- hash agility (sha256 + sha512)
- signature agility (pluggable verification; consider Sigstore/cosign integration points)
- FIPS considerations if required

### 9.3 FIPS compliance in Go (must-have)

- Treat FIPS as a build-and-runtime contract: build with a FIPS-capable Go toolchain, and run on a FIPS-enabled OS image where required.
- For RHEL-based deployments, prefer Red Hat’s Go toolset guidance for FIPS mode (build with the toolchain defaults; rely on the FIPS-enabled OpenSSL runtime). citeturn10search1
- Track upstream Go’s native FIPS 140-3 cryptographic module work and plan to adopt it when it is production-viable for Quay’s support matrix. citeturn10search5

**Agentic tasks (CI-enforceable):**
1. Add a `make fips-smoke` target that:
   - builds binaries in the FIPS toolchain container
   - runs minimal crypto self-tests (TLS handshake, HMAC, AES-GCM) under a FIPS-enabled base image
2. Add an automated check that rejects non-FIPS builds for downstream/enterprise release pipelines.

### 9.4 Auth modernization and hardening (without breaking contracts)

#### Goals

- Preserve every existing auth flow and credential type (strict compatibility).
- Internally normalize auth into **one** representation: `Principal + Scopes + Context`.
- Make automation access (robots/apps/tokens) simpler, auditable, and easier to rotate.
- Create a clear path to future deprecations (e.g., OAuth apps) via telemetry + warnings, not breaking changes.

#### Proposed internal model

Unify all inbound credentials into:

```go
type PrincipalType string
const (
  PrincipalAnonymous PrincipalType = "anonymous"
  PrincipalUser      PrincipalType = "user"
  PrincipalRobot     PrincipalType = "robot"
  PrincipalApp       PrincipalType = "app"
)

type Principal struct {
  Type PrincipalType
  ID   string // user_id / robot_id / app_id
  Org  string // optional: owning org
}

type AuthContext struct {
  Principal Principal
  Scopes    []string
  TokenID   string // for audit/rotation
}
```

#### Compatibility layer (what must be supported)

**Contract rule:** validation must accept all current credential formats (Basic, Bearer, legacy “special usernames”, OAuth tokens, robot tokens, etc.), and must resolve them to the same permissions as Python.

Quay historically validates “username + password/token” combinations and has special handling for access tokens. citeturn7search3
(Agents will extract the complete matrix from the current Python auth code and encode it as tests.)

#### Implementation plan (agentic + TDD)

1. **Golden auth fixtures (first):**
   - Create `go/internal/auth/testdata/` with fixtures for each flow:
     - user password login
     - OAuth access token
     - robot token
     - app token
     - invalid/expired/revoked tokens
   - For each fixture, add a contract test that hits legacy and Go validation endpoints and asserts:
     - same success/failure
     - same resolved identity type
     - same scope/permission outcome

2. **Auth library (Go) with pluggable verifiers:**

```go
type Verifier interface {
  Name() string
  CanHandle(r *http.Request) bool
  Verify(ctx context.Context, r *http.Request) (*AuthContext, error)
}
```

- Implement verifiers incrementally (TDD):
  - `BasicAuthVerifier`
  - `BearerTokenVerifier`
  - `LegacySpecialUsernameVerifier` (if Quay uses them)
- The outer `Authenticator` tries verifiers in a stable priority order.

3. **Modernize automation tokens (without breaking old ones):**
   - Add a new token format for *newly created* robot/app tokens:
     - opaque, prefix-tagged (e.g., `quay_rbt_...`)
     - stored **hashed** in DB (bcrypt/argon2id depending on FIPS constraints; validate against your compliance requirements)
     - supports rotation + last-used timestamp
   - Legacy tokens continue to validate via legacy verifier.

4. **Deprecation posture (future):**
   - Add telemetry counters: token type usage by endpoint.
   - Add optional response headers/warnings for legacy flows (off by default; on in staging).
   - Publish a deprecation policy document—separate from the migration work.

#### Hardening requirements

- constant-time comparisons for secrets/tokens
- centralize token parsing/validation and scope evaluation
- audit logs for login/token issuance/permission changes (PII-safe)

---

## 10. Packaging and deployment: Kubernetes, VM, Mirror Registry, image size

### 10.1 Multi-image deployment (default)

Build separate images:
- `quay-edge-router`
- `quay-registryd`
- `quay-core-api`
- `quay-worker-*`

### 10.1.1 “Single application” run experience (required)

Even with multiple images, provide a **single-command** install/run UX:

- **Kubernetes:** Operator (or helm/kustomize) deploys the full set of Deployments/CronJobs.
- **Standalone VM:** ship a `quayctl` (or `quay`) tool that generates:
  - Podman **quadlets** (systemd units) for each component
  - a “profile” switch: `registry-only` vs `full`
- **Mirror Registry (disconnected):** update the bundle to include the multiple images + `quayctl`, so offline install still feels like “install Quay” rather than “assemble microservices”.

Example VM flow:

```bash
# unpack mirror bundle
./quayctl install --profile=registry-only --config=/etc/quay/config.yaml
sudo systemctl enable --now quay-registryd quay-edge-router
```

This avoids reintroducing a supervisor-style monolithic container while keeping UX simple.


### 10.2 Keeping images slim

Rules:
- multi-stage builds with static Go binaries where possible
- distroless/ubi-micro base images
- avoid bundling build tools, compilers, shells into production images
- split “full Quay” and “registry-only” builds so the registry-only bundle stays small

### 10.3 Mirror Registry (disconnected)

Mirror Registry can evolve to bundle multiple images in its offline tarball:
- include all required Quay component images
- install via podman and generate k8s manifests or quadlets accordingly
- provide a “registry-only” bundle option with fewer components

---

## 11. Team execution plan (4 people) + workstreams

Parallelize into four workstreams:

1. **Registry protocol work**: Distribution fork + schema v1 + digest agility.
2. **Platform/infra**: edge-router, deployment manifests, observability, CI.
3. **DB/storage**: metadata/sqlc, object storage adapters, connection pooling fixes.
4. **Workers**: inventory + conversion of GC/mirroring/notifications pipelines.

Cross-cutting rules:
- Every PR must add/extend tests.
- Every migrated endpoint must have a contract test.
- Performance regression checks on `/v2` endpoints are blocking.

---

## 12. Appendix: templates and examples

### 12.1 Service skeleton

```
go/cmd/core-api/main.go
go/internal/coreapi/server.go
go/internal/httpx/middleware.go
go/internal/metadata/...
go/internal/storage/...
```

### 12.2 Podman quadlet for core-api (VM)

```ini
[Unit]
Description=Quay core API

[Container]
Image=quay.io/quay/quay-core-api:latest
EnvironmentFile=/etc/quay/quay.env
Network=quay-net

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
```

### 12.3 Agent PR checklist

- [ ] Added failing test first (unit/integration/contract)
- [ ] Implemented minimal code to pass
- [ ] Updated contract fixtures (if endpoint behavior changed)
- [ ] Updated docs/manifests if needed
- [ ] Ran: go test, integration suite, contract suite, Playwright (if applicable)
