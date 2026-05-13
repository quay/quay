# Python Pain Points Integration Analysis

Status: Draft (revised after GPT-5.4 review)
Created: 2026-05-13
Revised: 2026-05-13

## 1. Purpose

This document maps each pain point from `Quay python pain points.md` to the current rewrite plan (`quay_rewrite.md` and its sub-plans), identifies what is already covered, and proposes specific changes. The goal is to ensure the rewrite does not simply port existing problems from Python to Go, while respecting the plan's core constraint of zero contractual regressions and safe incremental cutover.

Proposals are split into two categories:

- **Category A: Address during the rewrite.** Internal architecture improvements that do not change external contracts and directly reduce the risk of porting existing design debt into Go.
- **Category B: Design now, implement post-parity.** Product-level changes (new token types, new permission models, new config surfaces) that require external contract changes, schema evolution, or new user-facing behavior. The rewrite should make these *easier to build later* by establishing clean internal boundaries, but they should not gate migration milestones.

## 2. Summary of findings

The rewrite plan is overwhelmingly a **port-with-parity** effort. It is rigorous about maintaining behavioral contracts, cutover safety, and rollback capability. However, it largely preserves the existing design for auth, permissions, configuration, and user/org modeling. Several pain points that motivated the rewrite are not addressed by the current plan.

| Pain point | Plan coverage | Category | Verdict |
|---|---|---|---|
| Performance (gunicorn/gevent) | Implicitly solved by Go | A | Partially covered -- add baselines and monitoring |
| Large memory footprint | Implicitly improved by Go | A | Not covered -- add memory budgets |
| Slow startup time | Implicitly improved by Go | A | Not covered -- add startup time targets |
| Complex/confusing auth | Ported as-is (WS7) | A (middleware) / B (tokens) | Internal cleanup during rewrite; token redesign post-parity |
| Rigid policy framework | Not mentioned | A (middleware) / B (new permissions) | Internal cleanup during rewrite; permission expansion post-parity |
| Worker architecture (supervisord) | Eliminated at M5 | A | Largely covered -- add lifecycle refinements |
| Configuration (init-time only, no per-org) | D-002 switches only | A (reload framework) / B (per-org) | Reload framework during rewrite; per-org post-parity |
| Confusing user design | Not mentioned | B | Design clean domain model; implement post-M5 |
| Complex networking (nginx, tracing) | nginx eliminated at M5 | A (observability) / B (rate limiting) | Observability during rewrite; configurable rate limiting post-parity |
| Database issues (Peewee, dual ORM) | sqlc replaces Peewee | A | Well covered -- add monitoring refinements |

## 3. Pain-point-by-pain-point analysis

### 3.1 Performance issues with cooperative multitasking

**Category A** -- address during rewrite.

**Pain point:** Gunicorn + gevent creates cooperative multitasking where one bad request can hang a whole worker. No out-of-the-box metrics for worker saturation. Hard to debug.

**What the plan covers:**
- Go's goroutine model is preemptive and eliminates cooperative multitasking entirely. Inherently solved.
- `performance_budget.md` defines latency budgets (P50/P95/P99) relative to Python baselines.
- `registryd_design.md` includes per-route metrics and auth latency counters.

**What the plan does NOT cover:**
- Performance budgets are parity targets ("baseline + X%"), not improvement targets.
- No per-request resource tracking (CPU time, memory allocated, goroutines spawned).
- No saturation metrics for the Go HTTP server (active connections, goroutine pool utilization, request queue depth).
- No timeout/cancellation policy (context deadline strategy).

**Proposed changes:**

1. **`performance_budget.md`**: Add improvement tracking targets alongside parity gates. Parity gates block cutover (safety). Improvement targets are tracked and reported but do not block ownership flips:
   - P99 latency improvement target: baseline * 0.5.
   - Concurrency correctness: zero hung-worker incidents per canary period.

2. **`registryd_design.md`**: Add a section on request lifecycle observability:
   - Context deadline propagation from HTTP handler through DAL.
   - Per-request goroutine tracking (detect goroutine leaks).
   - Request-scoped resource accounting (DB queries executed, bytes read from storage, time in auth).

---

### 3.2 Large memory footprint

**Category A** -- address during rewrite.

**Pain point:** Each request creates huge overhead because gevent must keep context for each request. The memory footprint scales poorly with concurrent request count.

**What the plan covers:**
- Go's goroutine stack starts at ~4 KB (vs. gevent's much larger per-greenlet overhead). Inherently improved.
- `data_access_layer_design.md` specifies connection pooling.
- `image_strategy.md` tracks component elimination that reduces container memory.

**What the plan does NOT cover:**
- No memory budget anywhere. `performance_budget.md` has latency budgets but zero memory targets.
- No per-pod memory sizing guidance for Go vs. Python.
- No baseline memory measurement requirement in M0.

**Proposed changes:**

1. **`performance_budget.md`**: Add memory budget category:
   - `PB-MEM-IDLE`: Baseline memory at idle. Track improvement vs. Python baseline (non-blocking).
   - `PB-MEM-LOAD`: Memory under sustained load. Track improvement vs. Python baseline (non-blocking).
   - `PB-MEM-PEAK`: Peak memory during burst. Define acceptable ceiling.
   - Include memory in the 14-day baseline collection requirement (M0).

2. **`deployment_architecture.md`**: Add resource sizing guidance:
   - Recommended container memory limits for Go vs. Python services.

---

### 3.3 Slow startup time

**Category A** -- address during rewrite.

**Pain point:** Pod startup takes more than a minute. Quay.io rollouts take 30+ minutes. Large deployments are painfully slow to update.

**What the plan covers:**
- Go binaries start in milliseconds vs. Python's module import and initialization. Inherently improved.
- `deployment_architecture.md` mentions health probe and readiness endpoint requirements.
- `data_access_layer_design.md` mentions enum table pre-load at startup.

**What the plan does NOT cover:**
- No startup time target anywhere.
- No baseline measurement for Python startup time.
- No startup dependency ordering (DB -> Redis -> storage -> readiness).

**Proposed changes:**

1. **`performance_budget.md`**: Add startup time budget:
   - `PB-STARTUP-READY`: Time from process start to readiness probe passing. Target: < 5 seconds (vs. current 60+ seconds). This is a tracking target, not a cutover gate.
   - Include startup time in baseline collection.

2. **`deployment_architecture.md`**: Add startup sequencing section:
   - Define dependency order (DB -> Redis -> storage -> readiness).
   - Define graceful degradation if optional dependencies (Redis, Clair) are unavailable at startup.

---

### 3.4 Complex/confusing auth

**Category A** (middleware centralization) / **Category B** (new token types, unified auth).

**Pain point:**
- 4 different auth methods for the API.
- Quay internal API treated differently than v2 registry API.
- OAuth tokens are per-org but represent a user.
- No global API token. Tokens are org-scoped.
- Superuser logic is sprinkled everywhere.

**What the plan covers:**
- `auth_backend_inventory.md` inventories 6 backends and 8 auth mechanisms.
- WS7 (Auth and identity parity) migrates all auth backends with conformance tests.
- WS12 (Route auth verification) verifies auth modes on all 413 routes.
- `auth_backend_inventory.md` section 5 defines a two-pipeline architecture (ValidateResult mechanisms vs. registry JWT path) and explicitly warns against forcing both through one abstraction.

**What the plan does NOT cover:**
- The plan ports all auth complexity as-is. No simplification, no unification.
- No centralized auth middleware -- auth decisions remain inline in endpoint code.
- No plan for global API tokens, OAuth scoping fixes, or robot/human credential convergence.
- Superuser logic will be re-sprinkled in Go instead of Python.

**Category A proposals (internal architecture -- address during rewrite):**

1. **`quay_rewrite.md` section 1 (Scope)**: Add:
   - "Centralize auth decision-making into middleware layers. Respect the two-pipeline constraint from `auth_backend_inventory.md` section 5: ValidateResult-style mechanisms and registry JWT identity context must remain distinct middleware chains. Auth checks must not be inline in endpoint business logic."

2. **Expand WS7 scope in `implementation_backlog.md`**:
   - Add deliverable: "Auth middleware layers for both pipelines. Endpoint handlers receive resolved identity context, not raw credentials."
   - Add deliverable: "Superuser checks extracted into middleware/interceptor. No inline `is_superuser()` calls in endpoint handlers."

3. **`registryd_design.md` and `api_surface_inventory.md`**: Add an architectural constraint:
   - "Go endpoint handlers must not import or call auth evaluation functions directly. Auth is resolved by middleware before the handler executes."

**Category B proposals (product changes -- design now, implement post-parity):**

4. **New design note (append to `auth_backend_inventory.md` or create `plans/rewrite/auth_evolution_roadmap.md`)** as a lightweight design note, not a blocking sub-plan:
   - Target state: unified token model (PAT) that works across v1 and v2 APIs.
   - Target state: global API tokens not scoped to a single org.
   - Target state: robot accounts authenticate via same mechanism as human users.
   - These are post-M5 product deliverables. The rewrite enables them by centralizing auth middleware (Category A), but does not ship new token types during migration.

---

### 3.5 Rigid policy framework

**Category A** (middleware layer) / **Category B** (new permission types).

**Pain point:**
- Policy decisions are inline instead of pre/post request handlers.
- Permission model is outdated with limited, rigid permissions.
- Cannot do per-repo or per-sub-path permissions.
- Should have a policy engine similar to cloud IAM.

**What the plan covers:**
- Nothing. No sub-plan mentions policy engine design, permission model redesign, or authorization middleware.
- `auth_backend_inventory.md` covers authentication, not authorization.

**Category A proposals (internal architecture -- address during rewrite):**

1. **`quay_rewrite.md` section 1 (Scope)**: Add:
   - "Authorization checks must be implemented as middleware or interceptors, not inline in endpoint handlers. The initial implementation reproduces current permission semantics exactly through the middleware layer."

2. **Expand WS7 or add WS7a in `implementation_backlog.md`**:
   - Add deliverable: "Authorization middleware that evaluates current permission model. Endpoint handlers call a single `Authorize(ctx, resource, action)` function. Initial policy replicates existing Python permission behavior exactly."
   - Done criterion: "All migrated endpoints use authorization middleware. No inline permission checks in handler bodies."

3. **`quay_rewrite.md` section 7 (Global quality gates)**: Add:
   - "Authorization checks are in middleware, not inline in endpoint handlers."

**Category B proposals (product changes -- design now, implement post-parity):**

4. **New design note (append to existing doc or create `plans/rewrite/authorization_evolution_roadmap.md`)** as a lightweight design note:
   - Target state: per-repo and per-namespace permissions.
   - Target state: pluggable policy evaluator interface (internal implementation initially, with a path to external engines like OPA/Cedar).
   - Target state: data-driven permission types (new permissions without code changes).
   - These are post-M5 product deliverables. The rewrite enables them by establishing the middleware boundary (Category A), not by shipping new permission types.

---

### 3.6 Worker architecture (supervisord-based)

**Category A** -- address during rewrite.

**Pain point:**
- Based on supervisord, a lift from VM architecture.
- Worker processes run even when features are disabled.
- Unnecessary bloat, increased memory and CPU.
- Hard to determine correct worker count per pod per application.

**What the plan covers:**
- `image_strategy.md` explicitly targets supervisord elimination at M5.
- `workers_inventory.md` maps all 36 supervisor programs.
- `deployment_architecture.md` specifies separate Deployments per worker family in Kubernetes.
- Master plan section 4 specifies "separate processes for enterprise; in-process goroutines for mirror mode."

**Proposed changes:**

1. **`deployment_architecture.md`**: Add a section on worker lifecycle:
   - Feature-gated startup: Go workers check their feature flag at startup and exit cleanly if the feature is disabled. No idle workers consuming resources.
   - Autoscaling signals: define which metrics drive worker scaling (queue depth, processing latency, error rate).
   - Resource profiles: recommended CPU/memory requests per worker type.

2. **`workers_inventory.md`**: Add columns for feature flag controlling each worker and expected resource profile.

3. **M4 exit criteria addition**: "Worker resource profiles documented. Autoscaling signals defined for queue-based workers."

This pain point is **largely covered** by the plan. The changes above are refinements.

---

### 3.7 Configuration (init-time only, no per-org)

**Category A** (runtime reload framework) / **Category B** (per-org config).

**Pain point:**
- Configuration changes require pod restart. Cannot change config at runtime.
- No per-org configuration. Only global config, preventing per-org feature monetization.
- Cannot quickly enable/disable changes without deploy (canary, Unleash-style).

**What the plan covers:**
- D-002 (approved) adds runtime config polling for migration switches with < 30s propagation.
- `config_tool_evolution.md` updates config validation for new switch/runtime keys.
- `switch_spec.md` defines a three-level resolution hierarchy.

**Category A proposals (internal architecture -- address during rewrite):**

1. **Extend D-002's config-provider polling to general feature flags**: The runtime polling infrastructure built for migration switches should be designed to support general feature flags from the start. This is an architectural choice in how the polling/notification framework is built, not new product scope.

2. **Add to `config_tool_evolution.md`**: Define which config categories are runtime-reloadable vs. restart-required:
   - Restart-required: DB connection strings, storage backend selection, auth backend selection, TLS certificates.
   - Runtime-reloadable (via D-002 polling): feature flags, migration switches, rate limit thresholds, quota overrides.
   - This categorization is a design-time decision that costs nothing to make now but is expensive to retrofit.

**Category B proposals (product changes -- design now, implement post-parity):**

3. **New design note (append to `config_tool_evolution.md`)**: Per-org config roadmap:
   - Target state: global defaults overridable per-org for specific settings (quotas, feature flags, rate limits).
   - This implies persistence model, precedence semantics, cache invalidation, admin APIs, UI surfaces, audit, and rollback behavior -- all post-M5 scope.
   - The rewrite enables this by building the reload framework (Category A) with an extensibility point for per-org overrides.

---

### 3.8 Confusing user design

**Category B** -- design now, implement post-M5.

**Pain point:**
- Users and orgs are the same entity but orgs are "special" users.
- Cannot have a single email for multiple orgs.
- SSO integration requires both a "quay" username and an SSO username.
- Robot users can call v2 API but not v1 API. OAuth tokens can call v1 API but not v2 API.

**What the plan covers:**
- Nothing. User/org data model ported as-is.
- `db_migration_policy.md` forbids breaking schema changes during mixed runtime.

**Why this is Category B:**
The user/org conflation is deeply embedded in the database schema, API response shapes, and UI. Changing it is a data migration and an external contract change, not just a code change. The master plan explicitly freezes breaking schema changes until after Python retirement, and this is the right call -- attempting identity model changes during mixed-runtime coexistence risks subtle semantic mismatches between Python and Go that would be extremely hard to debug.

**Proposed changes:**

1. **`data_access_layer_design.md`**: Add a design note:
   - "Go domain types for User, Organization, and ServiceAccount should use distinct types internally. The DAL maps these to the shared `user` table during mixed-runtime. This separation enables future schema evolution without changing business logic."
   - This is a zero-cost architectural choice that makes the post-M5 evolution easier. It does not change external behavior or DB schema.

2. **New design note (create `plans/rewrite/identity_evolution_roadmap.md`)** as a lightweight future-state document:
   - Target state: separate Account, Organization, and ServiceAccount entities.
   - Target state: SSO identity as primary identity.
   - Target state: unified credential model for robots and humans.
   - Implementation timeline: post-M5, after Python retirement and schema freeze is lifted.

---

### 3.9 Complex networking

**Category A** (observability) / **Category B** (configurable rate limiting).

**Pain point:**
- nginx sits in front of gunicorn, adding routing logic separate from Flask routing.
- Rate limiting is implemented at the nginx level, poorly, with no user configuration.
- No traceability -- cannot track what resources a request consumes, what DB calls it makes.

**What the plan covers:**
- Master plan section 5.1 describes nginx's role during coexistence and its elimination at M5. The plan explicitly relies on nginx's production-hardened rate limiting, buffering, and timeout tuning during the migration period.
- `tls_security_posture.md` covers TLS termination policy.
- `registryd_design.md` includes per-route metrics.

**Category A proposals (observability -- address during rewrite):**

1. **Add observability requirements to existing plans** rather than a separate sub-plan. Specifically, add to `quay_rewrite.md` section 7 (Global quality gates):
   - "Every request has a trace ID propagated through all layers (HTTP handler, auth, DAL, storage)."
   - "Structured JSON logging with request context is the default for all Go services."
   - "Per-request resource accounting is available via structured log fields or trace spans (DB query count/duration, storage bytes, auth decision time)."
   - "Prometheus-compatible metrics are exposed for all Go services (request count, latency histogram, error rate, active connections, goroutine count, DB pool utilization)."

2. **`registryd_design.md`**: Expand the existing metrics section to include trace context propagation and structured logging requirements.

3. **`performance_budget.md`**: Add observability as an M0 baseline requirement:
   - "Go services must emit trace IDs and structured logs from the first canary deployment. Baseline capture includes observability coverage audit."

**Category B proposals (rate limiting -- implement when nginx is removed):**

4. **Design note appended to `deployment_architecture.md` or `tls_security_posture.md`**: Rate limiting roadmap:
   - During coexistence (M1-M4): nginx continues to handle rate limiting. No changes.
   - At M5 (nginx removal): Go must absorb rate limiting. Design a Go-native rate limiting middleware at that point.
   - Target state: per-endpoint, per-org, per-user configurable rate limits with standard `RateLimit-*` headers.
   - This is naturally gated by nginx removal at M5, not an independent deliverable.

---

### 3.10 Database issues

**Category A** -- address during rewrite.

**Pain point:**
- Peewee connection pooling causes a huge number of DB connections.
- Peewee-generated queries are complex and hard to debug/optimize.
- Dual ORM: SQLAlchemy for migrations (Alembic), Peewee for queries. Confusing.

**What the plan covers:**
- `data_access_layer_design.md` specifies sqlc for query generation (replacing Peewee). All queries are explicit SQL.
- Connection pooling via Go's `database/sql` with configurable limits.
- Read-replica routing with fallback.
- N+1 query protection as a design requirement.
- Schema drift CI gate detects divergence between Alembic and sqlc.

**Proposed changes:**

1. **`performance_budget.md`**: Add database budget:
   - `PB-DB-CONN`: Max DB connections per Go service instance. Track improvement vs. Python baseline (non-blocking).
   - `PB-DB-QUERY-P99`: P99 query latency. Track improvement vs. Python baseline (non-blocking).
   - Slow query logging: log queries exceeding configurable duration threshold.

2. **`data_access_layer_design.md`**: Add monitoring requirements:
   - Expose active/idle/waiting connection counts as Prometheus metrics.
   - Structured log entry for queries exceeding configurable duration threshold.

This pain point is **well covered** by the plan. The changes above are monitoring refinements.

---

## 4. Cross-cutting observations

### 4.1 Parity gates vs. improvement targets

The plan's performance budgets are safety-oriented: "baseline + 10%" gates ensure the rewrite is not worse. This is correct for migration safety. However, the pain points document exists because current performance is unacceptable -- the rewrite should also track improvement.

**Proposed change:**

Add an "improvement tracking" section to `performance_budget.md`, clearly separated from parity gates. Improvement targets are tracked and reported but **do not block cutover**. Missing improvement targets are reported with rationale, not treated as failures.

| Metric | Python baseline | Parity gate (blocks cutover) | Improvement target (tracked, non-blocking) |
|---|---|---|---|
| P99 latency (pull) | TBD | baseline + 10% | baseline * 0.5 |
| Memory per pod | TBD | N/A (no current gate) | baseline * 0.3 |
| Startup time | TBD | N/A (no current gate) | < 5s |
| DB connections per pod | TBD | baseline | baseline * 0.5 |

### 4.2 External contracts vs. internal architecture

The plan's default stance is to preserve every behavior exactly. This is correct for external API contracts (users depend on them) but overly conservative for internal architecture.

**Proposed change:**

Add a section to `quay_rewrite.md` distinguishing between:
- **External contracts** (API shapes, auth token formats, DB schema during mixed runtime): must be preserved exactly. Changes here are Category B (post-parity).
- **Internal architecture** (auth middleware, authorization checks, config loading, domain model types): should be improved where pain points are documented, as long as external behavior is unchanged. Changes here are Category A (during rewrite).

This distinction provides a principle for deciding which improvements are in-scope without case-by-case debate.

### 4.3 Auth pipeline constraint

`auth_backend_inventory.md` section 5 defines a two-pipeline architecture:
- Pipeline A: ValidateResult-style mechanisms (basic, cookie, oauth, ssojwt, signed_grant, credentials, federated).
- Pipeline B: Registry JWT identity-context path.

The inventory explicitly warns: "Do not force both pipelines through one middleware abstraction if it changes behavior/identity semantics."

Any auth centralization work (Category A) must respect this constraint. "Centralize" means extracting auth out of inline handler code into middleware -- it does not mean collapsing the two pipelines into one.

## 5. Proposed changes to existing plans

### 5.1 Changes to `quay_rewrite.md`

**Section 1 (Scope)** -- add:
- "Centralize auth decision-making into middleware layers, respecting the two-pipeline constraint. Auth checks must not be inline in endpoint business logic."
- "Authorization checks must be implemented as middleware, not inline in endpoint handlers."

**Section 7 (Global quality gates)** -- add:
- "Every request has a trace ID propagated through all layers."
- "Structured JSON logging is the default for all Go services."
- "Auth and authorization checks are in middleware, not inline in endpoint handlers."
- "Startup time within budget."

**New section between 4 and 5** -- "External contracts vs. internal architecture":
- Define the distinction and establish the principle that internal architecture improvements are in-scope for the rewrite.

### 5.2 Changes to `performance_budget.md`

- Add memory budgets (`PB-MEM-IDLE`, `PB-MEM-LOAD`, `PB-MEM-PEAK`).
- Add startup time budget (`PB-STARTUP-READY`).
- Add database budgets (`PB-DB-CONN`, `PB-DB-QUERY-P99`).
- Add improvement tracking section (non-blocking targets).
- Expand M0 baseline capture to include memory, startup time, and DB connection counts.

### 5.3 Changes to `implementation_backlog.md`

- **WS7**: Add auth middleware deliverables (both pipelines) and superuser extraction.
- **WS7 or new WS7a**: Add authorization middleware deliverable (current permissions through middleware layer).
- Add observability requirements to WS3 (registry) and WS4 (API) entry criteria.

### 5.4 Changes to `deployment_architecture.md`

- Add worker lifecycle section (feature-gated startup, autoscaling signals, resource profiles).
- Add startup sequencing section (dependency order, graceful degradation).
- Add resource sizing guidance for Go vs. Python services.

### 5.5 Changes to `workers_inventory.md`

- Add feature flag and resource profile columns.

### 5.6 Changes to `config_tool_evolution.md`

- Add runtime-reloadable vs. restart-required config categorization.
- Add per-org config roadmap design note (post-M5).

### 5.7 Changes to `data_access_layer_design.md`

- Add distinct Go domain types design note (User/Organization/ServiceAccount).
- Add connection count and slow query monitoring requirements.

### 5.8 Changes to `registryd_design.md`

- Add request lifecycle observability section (trace context, resource accounting).

## 6. New documents (lightweight design notes, not blocking sub-plans)

Rather than six new sub-plans that would increase M0 planning drag, create lightweight design notes that capture future-state direction without gating the migration:

| Document | Type | Content | Blocks migration? |
|---|---|---|---|
| `auth_evolution_roadmap.md` | Design note | Unified token model, global tokens, credential convergence | No |
| `authorization_evolution_roadmap.md` | Design note | Per-repo permissions, pluggable policy evaluator, IAM path | No |
| `identity_evolution_roadmap.md` | Design note | User/org/service account separation, SSO simplification | No |
| Appended to `config_tool_evolution.md` | Section | Per-org config overlay model | No |
| Appended to `deployment_architecture.md` | Section | Rate limiting roadmap (post-nginx-removal) | No |

These documents record the team's intent to address pain points post-parity. They inform architectural choices made during the rewrite (e.g., clean domain types, middleware boundaries) without expanding migration scope.

## 7. Open decisions to add

| ID | Decision | Suggested owner | Category | Rationale |
|---|---|---|---|---|
| D-009 | Observability stack selection | runtime-platform | A | OpenTelemetry integration scope. Should be decided before WS3 implementation. |

D-009 is the only new decision that is migration-blocking. Auth simplification, authorization expansion, and per-org config are Category B and should be captured as roadmap items, not as open migration decisions competing with the already-unresolved D-006 through D-008.

## 8. Milestone impact

### M0 additions
- Expand 14-day baseline capture to include memory, startup time, and DB connection counts.
- Decide D-009 (observability stack).
- Approve observability requirements (additions to existing quality gates, not a separate sub-plan).

### M2 additions
- Trace IDs and structured logging operational for registry routes.
- Request-scoped resource accounting available for registry hot paths.

### M3 additions
- Auth middleware centralization complete (both pipelines, respecting two-pipeline constraint).
- Authorization middleware operational (current permissions through middleware, no inline checks in handlers).

### M4 additions
- Worker resource profiles documented with autoscaling signals.
- Feature-gated worker startup validated.

### M5 additions (existing scope, no new exit criteria)
- nginx removal already in scope -- rate limiting absorption happens naturally at this point.
- Identity evolution and per-org config roadmap documents exist as approved design notes for post-M5 work.

## 9. Recommended next steps

1. **Immediate**: Review this analysis with the pain points authors. Confirm Category A/B classification.
2. **Before M0 gate**: Add memory, startup, and DB baselines to the 14-day capture (low effort, high value).
3. **Before M0 gate**: Add observability requirements to `quay_rewrite.md` quality gates and decide D-009.
4. **Before M0 gate**: Add the "external contracts vs. internal architecture" distinction to `quay_rewrite.md`.
5. **Before WS3/WS4 starts**: Ensure auth middleware and authorization middleware requirements are in WS7 scope.
6. **During M0-M3**: Draft the three lightweight evolution roadmap documents (auth, authorization, identity). These inform architectural choices but do not gate milestones.
7. **At M5**: Review evolution roadmaps and decide which post-parity improvements to prioritize.

## 10. Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Auth checks remain inline, requiring later refactor | High (current plan trajectory) | High -- touches all endpoints | Add auth middleware to WS7 scope (Category A) |
| Permissions remain inline, requiring later refactor | High (current plan trajectory) | High -- in every handler | Add authorization middleware to WS7/WS7a scope (Category A) |
| Observability is an afterthought | Medium | High -- Go harder to debug than Python | Make observability an M0 quality gate (Category A) |
| Improvement targets never set, rewrite delivers parity only | High | Medium -- missed opportunity | Add non-blocking improvement tracking to performance_budget.md |
| Post-parity improvements never happen because no roadmap exists | Medium | High -- pain points persist in Go | Create lightweight evolution roadmaps during M0-M3 |
| Category B work creeps into migration scope | Medium | High -- delays migration | Enforce Category A/B distinction in planning reviews |
| Identity model stays conflated indefinitely | High | Medium -- UX impact | Clean Go domain types (Category A) enable future evolution |
