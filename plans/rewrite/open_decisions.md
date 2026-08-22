# Open Decisions Register

Status: Active (3 open decisions)
Last updated: 2026-02-12

## 1. Purpose

Track planning decisions that block or materially change implementation sequencing.

## 2. Decision table

| ID | Decision | Status | Suggested owner | Target approval date | Current evidence | Recommended default | Impact if delayed |
|---|---|---|---|---|---|---|---|
| D-001 | `ip-resolver-update-worker` disposition | approved | runtime-platform | 2026-02-13 | Present in `conf/init/supervisord_conf_create.py`; no supervisor program block; no worker implementation found in repo (`ip_resolver_update_worker_disposition.md`) | Remove stale service-map entry and treat as retired unless concrete worker implementation is introduced | Worker tracker remains blocked and ownership controls stay ambiguous |
| D-002 | Production switch transport | approved | control-plane | 2026-02-13 | Switch model defined in `switch_spec.md`; transport options in `switch_transport_design.md` | Adopt Option B: config-provider backed runtime polling with `<30s` propagation and fallback-to-python on parse failure | Rollback may require deploy/restart; canary safety reduced |
| D-003 | DB exception governance | approved | db-architecture | 2026-02-20 | Policy exists in `db_migration_policy.md`; approvers/process now documented in backlog/gates | Require explicit migration exception record + designated approvers before non-additive changes | Risk of untracked breaking schema changes during mixed runtime |
| D-004 | Operational CLI tooling disposition | approved | release-management | 2026-02-20 | `operational_tooling_plan.md` + tooling inventory identify scripts requiring disposition | Treat tooling scripts as `retire-approved` by default unless transition-period exception is approved | Python dependency may linger and block retirement gate |
| D-005 | Repo mirror implementation path (`skopeo` subprocess vs Go `containers/image`) | approved | registry-platform | 2026-02-09 | User approved Go-native migration on 2026-02-09; source anchor: `util/repomirror/skopeomirror.py` | Migrate to Go-native `containers/image`; keep temporary compatibility fallback only during transition testing | Mirror/image workstreams proceed with finalized dependency direction |
| D-006 | Go HTTP router: `chi/v5` vs `net/http` (stdlib) | open | runtime-platform | 2026-02-26 | Plan specifies `chi/v5` in `registryd_design.md` §3 and `go_module_strategy.md`. quay-distribution uses `gorilla/mux` (archived). Neither doc justifies the choice over stdlib `net/http`, which supports method+path routing since Go 1.22. | See options below (§4) | Router choice is embedded in every handler registration across 413 routes; changing later is a large mechanical refactor. Decide before WS3/WS4 implementation begins. |
| D-007 | Coexistence deployment topology: where does the Go binary run during M1-M4? | open | deployment-platform | 2026-02-26 | Master plan §5.1 claims nginx routes to Go as "just a config change (`proxy_pass` target)". This is only true if Go runs in the same container as nginx. `image_strategy.md` §3 says M0-M1 uses "Go sidecar/service images" — implying separate containers. `deployment_architecture.md` describes the end-state but not the transition-state topology. The plan does not specify where the Go binary runs relative to nginx during coexistence. | See options below (§5) | Blocks M1 (edge routing and ownership controls). nginx config generation, container image composition, and Quay Operator changes all depend on this. If delayed, WS2 and WS11 cannot produce testable artifacts. |
| D-008 | Upload hasher state cross-runtime strategy: capability-level split vs UUID pinning vs shared format | open | registry-platform | 2026-02-26 | `registryd_design.md` §9 proposes UUID-based upload pinning (M2-M3) and a cross-runtime hasher serialization format (M4+). Neither mechanism is designed. The plan's existing capability-level switch hierarchy (`ROUTE_OWNER_CAP_V2_PULL` vs `ROUTE_OWNER_CAP_V2_PUSH`) may eliminate the need for both. | See options below (§6) | Blocks WS3 (registry migration) design. If the pinning/shared-format approach is kept, it requires routing-layer design for UUID-based session affinity and a cross-runtime serialization format for SHA-256 hasher internal state — both significant engineering efforts with no current design. |

## 3. Resolution rules

- Every decision must include: owner, due date, chosen option, and rollback implication.
- Resolved decisions are copied into relevant sub-plans.
- Approval outcomes are recorded in `plans/rewrite/decision_log.md`.
- Consolidated recommendations are maintained in `plans/rewrite/decision_approval_packet.md`.

## 4. D-006 option analysis: Go HTTP router

### Problem statement

The plan specifies `chi/v5` as the HTTP router (`registryd_design.md` §3, implied in `go_module_strategy.md`). The quay-distribution prototype uses `gorilla/mux` (archived, maintenance-only). Neither document justifies the choice over Go's standard library `net/http`, which gained method-based routing and path parameters in Go 1.22 (Feb 2024).

The Go binary will target Go 1.24+. At that version, `net/http.ServeMux` natively supports:

```go
mux.HandleFunc("GET /v2/{name}/manifests/{reference}", handleGetManifest)
mux.HandleFunc("PATCH /v2/{name}/blobs/uploads/{uuid}", handlePatchUpload)
```

This decision affects every handler registration across 413 routes. Changing the router after implementation begins is a large mechanical refactor.

### Option A: `net/http` (stdlib)

Advantages:
- Zero external dependency. No version pinning, no supply-chain audit, no CVE tracking for the router.
- Simpler FIPS compliance — one fewer dependency in the build.
- Go 1.22+ `ServeMux` covers method routing, path parameters, and host matching.
- Longest possible support lifetime — supported as long as the Go version is supported.
- Smaller binary size (marginal).

Disadvantages:
- No built-in route grouping. Applying different middleware to `/v2/*` vs `/api/v1/*` vs `/health` requires manual composition (wrapper functions or helper patterns). With 12 route families and different auth requirements per family, this is real boilerplate.
- No built-in middleware chaining. Each middleware layer is a `func(http.Handler) http.Handler` wrapper — functional but verbose compared to chi's `r.Use()`.
- No subrouter mounting. `net/http` has no equivalent to `chi.Mount("/v2", v2Router)` for composing sub-routers from different packages.
- `distribution/v3` uses `gorilla/mux` internally. If registryd wraps distribution's handler, the outer router and distribution's inner router use different libraries regardless. This is manageable but not seamless.

### Option B: `chi/v5`

Advantages:
- Route grouping with per-group middleware (`r.Group()`, `r.Route()`, `r.Use()`). For 12 route families with different auth, rate-limit, and observability middleware, this reduces boilerplate significantly.
- Subrouter mounting (`chi.Mount()`) allows route families to be defined in separate packages and composed at the top level.
- `chi` is `net/http`-compatible — handlers are standard `http.Handler`/`http.HandlerFunc`. No lock-in to chi-specific interfaces. Migration away from chi is mechanical (extract middleware, flatten mounts).
- Active project, widely used in production Go services.

Disadvantages:
- External dependency that must be pinned, audited, and tracked for CVEs.
- Adds one entry to the FIPS supply-chain audit scope.
- Yet another router in the stack alongside `distribution/v3`'s internal `gorilla/mux`.

### Option C: `gorilla/mux` (status quo from prototype)

Not recommended. The project is archived and in maintenance-only mode. Adopting it for a multi-year project is a known technical debt decision.

### Recommendation

**Option A (`net/http`)** for the router itself. Write a thin internal helper package (`internal/httputil/` or similar, ~100 lines) that provides route-group and middleware-chain ergonomics on top of `net/http.ServeMux`. This avoids the external dependency while addressing the middleware composition concern. The helpers are simple functions, not a framework:

```go
// internal/httputil/group.go
func Group(mux *http.ServeMux, prefix string, middleware ...Middleware, routes func(*http.ServeMux)) {
    sub := http.NewServeMux()
    routes(sub)
    handler := Chain(sub, middleware...)
    mux.Handle(prefix+"/", http.StripPrefix(prefix, handler))
}
```

This keeps the dependency count minimal for a long-lived infrastructure project where FIPS compliance and 4-arch builds are in scope, while preserving the ergonomic grouping that chi would provide.

### Impacted sub-plans if approved

- `registryd_design.md` §3: remove `chi/v5` from dependency list
- `go_module_strategy.md`: remove `chi/v5` from dependencies
- `quay_distribution_reconciliation.md` §5.2: update divergent dependency table
- `architecture_diagrams.md` §7: no change (package layout doesn't reference router)

### Rollback implication

If `net/http` proves insufficient during implementation (unlikely given Go 1.22+ capabilities), adding chi later is a mechanical migration — chi uses standard `http.Handler` interfaces, so handlers don't change. Only registration code changes.

## 5. D-007 option analysis: coexistence deployment topology

### Problem statement

Master plan §5.1 says: "nginx acts as the front door during Python/Go coexistence. Go becomes an additional upstream and prefixes move from Python upstreams to the Go upstream as capabilities migrate. This approach requires zero new proxy code — nginx already does this."

This claim is only straightforwardly true if Go runs in the same process space where nginx can reach it at a known address without infrastructure changes. The plan does not specify where the Go binary runs during the M1-M4 coexistence period.

Today, nginx runs inside the Quay container (managed by supervisord) and proxies to gunicorn processes on localhost:

```nginx
# server-base.conf.jnj (simplified)
upstream registry_app_server { server localhost:8443; }
upstream web_app_server { server localhost:8112; }
upstream secscan_app_server { server localhost:8444; }
```

For Go to be "just another upstream," it must be reachable from nginx at a known, stable address. How this works depends entirely on where Go runs.

Meanwhile, `image_strategy.md` §3 says M0-M1 uses "Go sidecar/service images for canary capabilities" — implying separate containers. And `deployment_architecture.md` §3 describes separate Kubernetes Deployments for `api-service` and `registryd`. Neither document addresses the transition state where Python and Go must coexist.

There are three deployment models to consider, and the answer may be different for each:
1. Single-container (current `podman`/`docker` standalone deployments)
2. Quay Operator on Kubernetes
3. VM/bare-metal with systemd

### Option A: Same container — Go as additional supervisord program

Go binary runs inside the existing Quay container alongside Python, managed by supervisord. nginx proxies to `localhost:go-port`.

```ini
# Added to supervisord.conf.jnj
[program:registryd]
command=/usr/local/bin/quay serve registryd --port=8445
autostart=%(ENV_QUAY_REGISTRYD_ENABLED)s
```

```nginx
# Added to server-base.conf.jnj
upstream go_registry_server { server localhost:8445; }
```

Advantages:
- "Just a config change" is literally true. `proxy_pass` points to localhost.
- No networking, service discovery, or container orchestration changes.
- Single image to build, ship, and manage (simpler for standalone/mirror deployments).
- Rollback is stopping the supervisord program and reverting nginx config.
- Works identically for standalone container and VM deployments.

Disadvantages:
- Container image grows (includes both Python and Go binaries). During M0-M4, the image contains both runtimes.
- Resource isolation is weaker — Python and Go compete for memory/CPU within one cgroup.
- Contradicts `image_strategy.md` which says "add Go sidecar/service images."
- supervisord manages a Go binary, which is unusual (Go binaries are typically self-supervising).
- Harder to independently scale Python vs Go in Kubernetes.

### Option B: Separate containers — Go as sidecar or separate deployment

Go binary runs in its own container. nginx in the Python container (or a separate nginx container) proxies to the Go container.

For standalone deployments:

```yaml
# docker-compose or Quadlet
services:
  quay-python:
    image: quay.io/projectquay/quay:latest
    ports: ["8080:8080"]
  quay-go:
    image: quay.io/projectquay/quay-go:latest
    command: ["quay", "serve", "registryd", "--port=8445"]
```

```nginx
# nginx must now reference external container
upstream go_registry_server { server quay-go:8445; }
```

For Kubernetes:
- Quay Operator creates separate Deployments for Go services
- nginx ConfigMap updated to route to Go Service endpoints
- Or: Go runs as sidecar containers in the existing Quay pod

Advantages:
- Clean separation of runtimes. Independent scaling, resource limits, and failure domains.
- Consistent with `image_strategy.md` "sidecar/service images" language.
- Independent image builds — Go image is small (UBI + static binary), Python image unchanged.
- Kubernetes-native (separate Deployments with independent HPA).

Disadvantages:
- "Just a config change" is no longer true for standalone deployments. Operators must change their deployment topology (add a container, configure networking).
- nginx must reference an external address, requiring container DNS or explicit configuration.
- Adds deployment complexity during the coexistence period — operators manage two containers where they previously managed one.
- Mirror-mode and standalone operators (who chose Quay partly for simplicity) get a more complex setup during migration.
- Quay Operator must be updated to manage the new deployment topology before M1.
- Rollback requires stopping a container and reverting nginx config (slightly more complex than Option A).

### Option C: Hybrid — same container for standalone, separate for Kubernetes

Use Option A for standalone/mirror deployments (single container, supervisord manages Go). Use Option B for Kubernetes deployments (Operator manages separate Deployments).

Advantages:
- Standalone operators see no deployment topology change during migration.
- Kubernetes deployments get clean separation and independent scaling.
- nginx routing is `localhost` for standalone (simple) and Service endpoints for K8s (Operator-managed).
- Aligns with the existing split: standalone deployments use supervisord, K8s deployments use Operator.

Disadvantages:
- Two deployment models to test and maintain during coexistence.
- Image strategy diverges: standalone image has both runtimes, K8s images are split.
- Documentation and support burden is higher.

### Recommendation

**Option C (hybrid)**. Standalone and mirror deployments are the cases where simplicity matters most and where "just a config change" must be literally true. These operators don't have an orchestrator to manage multi-container topologies. For Kubernetes, the Operator already manages deployment topology and can handle separate Deployments cleanly.

Concrete actions if approved:
1. Add Go binary to the existing Quay container image starting at M1. Add supervisord program blocks for `registryd` and `api-service` (disabled by default, enabled by owner switches).
2. Update `server-base.conf.jnj` to include Go upstream blocks (conditionally included when Go programs are enabled).
3. Scope Quay Operator changes for separate Go Deployments as a WS11 deliverable.
4. Update `image_strategy.md` to reflect the hybrid model (single image for standalone, split images for K8s).
5. Update master plan §5.1 to explicitly state the deployment topology for each deployment model.

### Impacted sub-plans if approved

- `quay_rewrite.md` §5.1: add explicit topology description per deployment model
- `deployment_architecture.md`: add transition-state topology section
- `image_strategy.md` §3: revise M0-M1 image composition to reflect hybrid model
- `config_tool_evolution.md`: add validation for Go service port/address settings
- `switch_transport_design.md`: confirm switch propagation works in both topologies
- `rollout_playbooks.md`: add deployment-model-specific rollout steps

### Rollback implication

For standalone (Option A path): stop Go supervisord programs, revert nginx config. Single container, single operation.
For Kubernetes (Option B path): Operator scales Go Deployments to zero, reverts nginx ConfigMap. Standard Operator reconciliation.

## 6. D-008 option analysis: upload hasher state cross-runtime strategy

### Problem statement

When a client pushes a large container image layer, it sends the data in chunks across multiple HTTP requests. The server computes a SHA-256 hash incrementally — after each chunk, it saves the in-progress hash state to the database (`BlobUpload.sha_state`) so the next request can resume the computation. At finalization, the server verifies the completed hash matches the client's claimed digest.

Python serializes this in-progress hash state using `pickle` (a Python-only binary serialization format) plus base64 encoding. Go cannot deserialize Python pickle data, and Python cannot deserialize whatever format Go would use. This means if an upload starts in one runtime and a subsequent chunk is handled by the other runtime, the receiving runtime cannot read the saved hash state and the upload fails.

`registryd_design.md` §9 proposes two strategies:
1. **M2-M3: UUID-based upload pinning** — route all requests for a given upload UUID to whichever runtime started the upload. Requires the routing layer to track which runtime owns each active upload session.
2. **M4+: Cross-runtime hasher format** — replace pickle with a portable format (JSON/protobuf) that both runtimes can read/write.

Neither mechanism has a design. The pinning strategy requires upload-session-aware routing (not just URL-prefix routing). The shared format requires serializing the internal state of a SHA-256 hasher in a portable way, which is non-trivial — these are implementation-specific byte buffers, not application data.

However, the plan's existing capability-level switch hierarchy (`switch_spec.md` §3.1) already supports splitting read and write operations at the routing level, which may eliminate the need for either mechanism.

### Option A: Capability-level read/write split (recommended)

Use the existing switch hierarchy to route pull and push to different runtimes:

```
ROUTE_OWNER_CAP_V2_PULL=go        # GET manifests, GET blobs, GET tags, catalog
ROUTE_OWNER_CAP_V2_PUSH=python    # POST uploads, PATCH uploads, PUT uploads, PUT manifests, DELETE
```

All upload-related requests (start, chunk, finalize) are push-capability routes. When all push routes stay on Python, every upload session runs entirely within Python. No upload ever crosses runtimes. The hasher serialization format is irrelevant.

When Go's upload implementation is complete and tested, flip `V2_PUSH=go`. All *new* uploads start in Go with Go's own hasher format. In-flight Python uploads complete or expire (upload sessions have a `processing_expires` TTL, typically minutes to hours).

Advantages:
- Uses the switch infrastructure the plan already designs. No new routing mechanism.
- No cross-runtime hasher serialization needed — ever. Each runtime uses whatever format it wants.
- No upload-session-aware routing. nginx routes by URL path and method, which it already does.
- Eliminates the UUID pinning design, the shared hasher format design, and the cross-runtime upload continuation test matrix from the plan.
- Simpler to reason about: "pull is Go, push is Python" is easy to explain and monitor.

Disadvantages:
- `/v2` migration happens in two phases (pull first, push later) rather than all at once. This extends the coexistence window for `/v2` routes.
- Emergency rollback of push from Go to Python causes in-flight Go uploads to fail. Clients retry from scratch. This is acceptable — uploads are short-lived, clients handle retries, and emergency rollback is exceptional.

### Option B: UUID-based upload pinning (current plan, M2-M3)

Route all requests for a given upload UUID to the runtime that started the session. Requires:
- A shared store (Redis or DB) mapping upload UUIDs to owning runtime.
- nginx or the routing layer consulting this store on every upload request.
- Or: a cookie/header set at upload start that nginx uses for sticky routing.

Advantages:
- Allows `/v2` pull and push to migrate to Go simultaneously.
- No phase gap between pull and push cutover.

Disadvantages:
- No design exists for how the routing layer performs UUID-to-runtime lookup. nginx does not natively support this without Lua scripting or an external auth subrequest.
- Adds operational complexity — a new stateful routing dependency during the migration.
- Still requires the M4+ shared format to eventually allow true cross-runtime continuation (or must be kept permanently).
- Must handle edge cases: what happens when the pinning store is unavailable? When an upload UUID is unknown (session expired)?

### Option C: Cross-runtime hasher serialization format (current plan, M4+)

Design a portable serialization format for SHA-256 hasher internal state that both Python and Go can read/write. Both runtimes produce and consume the same format.

Advantages:
- Enables true cross-runtime upload continuation — any request can be handled by any runtime.
- No routing constraints beyond normal load balancing.

Disadvantages:
- SHA-256 hasher internal state is implementation-specific. Python's `hashlib` (backed by OpenSSL) and Go's `crypto/sha256` use different internal buffer layouts. Extracting and importing raw state requires low-level manipulation of each implementation's internals.
- Go's `crypto/sha256` supports `encoding.BinaryMarshaler`/`BinaryUnmarshaler` for its own state, but importing a foreign state layout requires custom code.
- Python's `hashlib` does not expose a public API for serializing/deserializing intermediate state in a portable format. The current approach uses `pickle` on the internal C object, which is CPython-specific.
- The format must be versioned and both runtimes must support old+new formats during rollout.
- Significant design and implementation effort for a problem that Option A avoids entirely.

### Recommendation

**Option A (capability-level read/write split)**. The plan's own switch hierarchy solves this problem without any new mechanism. Pull migrates to Go first (read-only, no hasher state involved). Push migrates to Go later as a single atomic flip. The cross-runtime hasher problem disappears because uploads never cross runtimes.

This simplification removes from the plan:
1. The UUID-based upload pinning mechanism (`registryd_design.md` §9 M2-M3 strategy)
2. The cross-runtime hasher serialization format (`registryd_design.md` §9 M4+ strategy)
3. The 4-scenario cross-runtime upload continuation test matrix (`registryd_design.md` §9 required tests)
4. Any routing-layer changes for upload session affinity

The only new requirement is that the M2 milestone splits into two sub-phases: M2a (pull parity) and M2b (push parity), with push staying on Python until Go's upload state machine is fully tested.

### Impacted sub-plans if approved

- `registryd_design.md` §9: replace pinning and shared-format strategies with capability-level split
- `registryd_design.md` §9 required tests: remove cross-runtime continuation scenarios, add pull/push independent cutover tests
- `quay_rewrite.md` §6 M2: note two-phase pull-then-push migration
- `cutover_matrix.md`: add `V2_PULL` and `V2_PUSH` as separate capability rows
- `architecture_diagrams.md` §5a/5b: update sequence diagrams to reflect split ownership during M2
- `rollout_playbooks.md` §3: add push cutover as a distinct rollout step after pull
- `test_strategy.md`: remove cross-runtime upload continuation from test planes

### Rollback implication

Pull rollback (`V2_PULL` go→python): config change, immediate. No state concerns — reads are stateless.
Push rollback (`V2_PUSH` go→python): config change. In-flight Go uploads fail; clients retry. Python resumes handling all new uploads immediately. Upload sessions have TTL expiry so no orphan cleanup is needed.
