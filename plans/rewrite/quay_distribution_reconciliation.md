# quay-distribution Reconciliation Report

Status: Draft (pending team review)
Last updated: 2026-02-11
Source: https://github.com/quay/quay-distribution

## 1. Purpose

Document the current state of `quay/quay-distribution`, its alignment with the rewrite plan in `quay_rewrite.md`, and provide actionable integration guidance. This report is intended to be used by a person or LLM to update the master plan and affected sub-plans after team review.

## 2. Repository overview

`quay/quay-distribution` is a working Go-based OCI container registry server that reads from Quay's existing PostgreSQL database and S3 storage. It was started in August 2025 and has been developed primarily by one engineer (Syed Ahmed, currently on leave), with contributions from jbpratt, davidlanouette, dancoe77, and sridipta.

| Field | Value |
|-------|-------|
| Repository | https://github.com/quay/quay-distribution |
| Language | Go |
| Go version | 1.24.0 (toolchain 1.24.9) |
| Default branch | main |
| Commits on main | 64 |
| Open feature PRs | 4 (#1 secscan, #13 rate limiting, #51 DB models, #74 sqlc POC) |
| Open dependabot PRs | 10 |
| Tags/releases | None (pre-release/experimental) |
| Created | 2025-09-04 |
| Last push | 2026-02-09 |
| CI | GitHub Actions (lint, test with race detection, build) |
| Contributors | syed (44 commits), dependabot (21), jbpratt (5), davidlanouette (4) |

## 3. What exists and works

### 3.1 Core registry server (60 Go source files)

- Serves `/v2/*` using `distribution/distribution/v3` as the OCI registry core
- Reads Quay's YAML config format (same field names as `conf/stack/config.yaml`)
- **Read-only**: handles pull (manifests, blobs, tags, catalog) but not push
- PutContent/Writer/Move/Delete all return `ErrUnsupportedMethod`

### 3.2 Authentication

- JWT bearer auth via JWK keys loaded from Quay's `servicekey` database table
- `pkg/auth/jwk/manager.go`: background key refresh (5-minute ticker, 1-hour full reload)
- `pkg/auth/quay/accesscontroller.go`: registered as `"quay"` auth backend with distribution
- Anonymous access for public repositories
- Access validation against JWT claims (repository/action matching, manifest digest, blob access)

### 3.3 Storage drivers (2 of 13 implemented)

- `pkg/storage/drivers/quay_s3/`: S3 presigned URLs for blob redirects, DB-backed manifest content reads, S3 HEAD for blob stat
- `pkg/storage/drivers/quay_akamai/`: wraps S3 driver, generates Akamai CDN URLs with EdgeAuth tokens, falls back to S3 direct for same-region AWS IPs
- Both registered via distribution's `factory.Register()` mechanism

### 3.4 Database layer

- `pkg/database/queries.go`: hand-written SQL queries using `database/sql` + `lib/pq`
- Queries: `GetRepositoryByName`, `GetManifestByDigest`, `GetManifestByTag`, `GetManifestDigestByTag`, `GetTagByName`, `CheckBlobExistsAsManifest`, `GetManifestBytes`, `GetBlobByDigest`, `ValidateBlobAccess`, `GetBlobStoragePath`, `BlobExistsInRepository`, `GetRepositoryIDByName`, `GetUserIDByUsername`
- `pkg/database/pool.go`: connection pool config, stats, health check
- `pkg/database/context.go`: global singleton for DB connection, cache, path parser
- `pkg/database/cache_wrapper.go`: generic `CachedQuery[T]()` function for JSON cache layer
- `pkg/database/models.go`: model structs for User, Repository, Manifest, Tag, ImageStorage, ManifestBlob, composite types

### 3.5 Caching

- `pkg/cache/interface.go`: `Cache` interface (Get/Set/Delete/Exists/Invalidate/Close)
- `pkg/cache/redis.go`: Redis implementation using `go-redis/v9`, connection pooling, key prefixing, pattern-based invalidation
- `pkg/cache/config.go`: 10 entity types with key format functions and configurable TTLs (Repository, Manifest, ImageStorage, Tag, Blob, etc.)
- `pkg/cache/factory.go`: factory with NoOpCache fallback and metrics recording

### 3.6 Observability

- `pkg/metrics/`: Prometheus metrics for HTTP (requests, duration, in-flight), DB pool (connections, wait time), cache (hits/misses, operation duration)
- `internal/tracing/`: OpenTelemetry with OTLP export, composite exporter, auto-export pattern, HTTP middleware via `otelhttp`
- Structured logging via Go's `slog` package (replaced logrus in Oct 2025)
- `pkg/utils/logging.go`: secret redaction for S3 keys, DB URLs, Akamai secrets, passwords, tokens

### 3.7 Action logs

- `pkg/actionlogs/`: Kinesis-based action log writer implementing distribution's `Listener` interface
- 26 action kinds mapped, with database-backed ID resolution
- HTTP context extractor for IP/user metadata

### 3.8 Infrastructure

- `Dockerfile`: multi-stage build with UBI 10 base, non-root user (UID 1000), debug variant with Delve
- `deploy/openshift/`: deployment template with RBAC, ServiceAccount, Deployment (health/readiness probes, resource limits), ClusterIP + NodePort services (ports 5000, 5443, 9091)
- `deploy/scripts/build_deploy.sh`: CI/CD build and push via skopeo
- Terraform configs for AWS (ALB, target groups)
- `.github/workflows/ci.yml`: golangci-lint, format check, test (race + coverage), build
- `.github/dependabot.yml`: Go modules (weekly), GitHub Actions (monthly), Docker (monthly)
- `.gitleaks.toml`: secret scanning rules for Quay/PostgreSQL/Akamai secrets
- HTTPS/TLS on port 5443, HTTP on port 5000
- Health check endpoints on `/health` and `/`
- Multi-phase graceful shutdown (SIGINT/SIGTERM, concurrent server shutdown, JWK manager stop, DB close)

### 3.9 Utilities

- `pkg/utils/ip_resolver.go`: AWS IP range resolver for Akamai CDN region bypass
- `pkg/utils/path_parser.go`: manifest/blob/layer path parsing, org/repo extraction
- `pkg/utils/context.go`: client IP extraction (X-Forwarded-For, X-Real-IP, RemoteAddr)
- `pkg/server/middleware/registry.go`: registry operation capture via regex path matching

## 4. Open PRs (in-progress work)

### 4.1 PR #74: sqlc POC (davidlanouette, Jan 2026)

**Status**: Open, no human review yet, +1371/-342 lines, 13 files

Proof-of-concept for auto-generating Go DB code from SQL definitions using sqlc. Implements a three-layer architecture:

1. **SQL layer** (hand-written): `schema.sql` (8 tables: user, repository, manifest, tag, imagestorage, manifestblob, uploadedblob, logentrykind) + `queries.sql` (15 named queries with sqlc annotations)
2. **Generated layer** (sqlc output): `db.go` (DBTX interface, Queries struct), `models.go` (raw models with `sql.Null*` types), `querier.go` (15-method interface), `queries.sql.go` (implementations)
3. **Domain layer** (hand-written): `types.go` (domain types using idiomatic Go `*string`/`*int64` with conversion functions), `quay_db.go` (wrapper adding caching, returning domain types)

**Relevance to plan**: Directly validates the DAL design in `data_access_layer_design.md` which specifies pgx/v5 + sqlc. The three-layer pattern (SQL definitions → generated code → domain wrappers) matches the plan's recommended approach. Key difference: PR uses `database/sql` driver; plan specifies `pgx/v5`.

Adds Makefile targets: `install-sqlc`, `sqlc-generate`.

### 4.2 PR #51: Database models from Python (davidlanouette, Nov 2025)

**Status**: Open, some review comments, +91/-24 lines, 4 files

Converts Python model classes to Go structs. Expands `User` from 7 to 22 fields, adds lookup tables (Visibility, RepositoryKind, MediaType, TagKind), adds autoprune models (NamespaceAutoPrunePolicy, RepositoryAutoPrunePolicy, AutoPruneTaskStatus), adds generic `Pointer[T]` helper.

**Note**: PR #51 and #74 have conflicting `models.go` files. PR #74 supersedes PR #51's model approach by generating models from SQL schema instead of hand-writing them.

### 4.3 PR #13: Rate limiting (dancoe77, Nov 2025)

**Status**: Open, changes requested, +1621/-0 lines, 5 files

Go middleware replacing nginx rate-limit config. Token bucket algorithm via `golang.org/x/time/rate`. Tier-based (very light/light/heavy/namespace auth), protocol-aware (HTTP/1 vs HTTP/2), namespace exemptions, miner-tag blocking, stale limiter cleanup.

**Reviewer feedback (blocking)**:
- davidlanouette: in-process rate limiting is insufficient for multi-instance deployments; needs shared backend (Redis) or proxy. Recommends `chi/httprate` with Redis backend.
- jbpratt: requested changes on code structure, naming, removing example command, moving docs to godoc, production-ready request ID generation, reconsidering miner-tag blocking approach.

**Relevance to plan**: Rate limiting is currently handled by nginx in Python Quay. The plan does not explicitly address rate limiting migration. This PR demonstrates the scope of the problem but the implementation approach needs rework for multi-instance correctness.

### 4.4 PR #1: Secscan rewrite (sridipta, Sep 2025)

**Status**: Open, 37 commits, stale since Sep 2025

Original prototyping branch with the earliest development history plus sridipta's security scanner integration. Contains WIP commits from initial development. Likely needs to be restarted rather than merged as-is.

## 5. Dependency comparison

### 5.1 Shared dependencies (plan and quay-distribution agree)

| Dependency | quay-distribution version | Plan reference |
|---|---|---|
| `distribution/distribution/v3` | v3.0.0 | `registryd_design.md` |
| `golang-jwt/jwt/v5` | v5.3.0 | `registryd_design.md`, `fips_crypto_migration.md` |
| `prometheus/client_golang` | v1.23.2 | `registryd_design.md` |
| `redis/go-redis/v9` | v9.17.2 | `redis_usage_inventory.md` |
| OpenTelemetry (`otel`, `otel/sdk`, `otel/trace`) | v1.39.0 | `registryd_design.md` |
| `aws/aws-sdk-go-v2` (S3, config, credentials) | v1.41.0 | `storage_backend_inventory.md` |
| `opencontainers/go-digest` | v1.0.0 | Implied by OCI spec |
| `google/uuid` | v1.6.0 | Common utility |

### 5.2 Divergent dependencies

| Area | quay-distribution | Plan specifies | Resolution needed |
|---|---|---|---|
| HTTP router | `gorilla/mux` v1.8.1 | `chi/v5` | gorilla/mux is archived/maintenance-only. Migrate to chi. Similar API, straightforward migration. |
| SQL driver | `lib/pq` (+ `database/sql`) | `pgx/v5` + `pgxpool` | Switch to pgx. PR #74's sqlc config would need `sql_package: "pgx/v5"` instead of `database/sql`. |
| YAML parser | `gopkg.in/yaml.v2` | Not specified | yaml.v3 is the current version. Consider upgrading during integration. |
| Akamai EdgeAuth | `mobilerider/EdgeAuth-Token-Golang` | Not specified | Niche dependency. Evaluate if it's maintained; if not, vendor or reimplement. |
| Kinesis | `aws/aws-sdk-go-v2/service/kinesis` | Not specified | Action logs to Kinesis is a Quay feature. Plan doesn't explicitly cover action log destination migration but this handles it. |

### 5.3 Missing from quay-distribution (plan requires, not yet implemented)

| Dependency | Plan reference | Purpose |
|---|---|---|
| `jackc/pgx/v5` + `pgxpool` | `data_access_layer_design.md` | DB driver with connection pooling |
| `sqlc-dev/sqlc` (build tool) | `data_access_layer_design.md` | Query code generation (PR #74 uses it but not yet merged) |
| `spf13/cobra` | OMR proposal, `quay_rewrite.md` §4 | CLI subcommands (`serve`, `install`, `config`, `migrate`) |
| `jackc/pgerrcode` | `data_access_layer_design.md` | Error classification for retry logic |
| FIPS crypto packages | `fips_crypto_migration.md` | AES-CCM, bcrypt, HMAC-SHA1 compat |
| SQLite driver | `quay_rewrite.md` §4 (mirror mode) | Embedded DB for mirror mode |

## 6. Structural divergences

### 6.1 Module path

- **quay-distribution**: `github.com/quay/quay-distribution`
- **Plan**: `github.com/quay/quay` (single module in main repo per `go_module_strategy.md`)
- **Action**: Move code into main quay repo. The separate repo was a prototyping convenience.

### 6.2 Package layout

- **quay-distribution**: uses `pkg/` (exported, importable by external code)
- **Plan**: uses `internal/` (unexported, prevents external import)
- **Action**: Rename `pkg/` → `internal/` during integration. This is a one-time mechanical change.

Mapping:

| quay-distribution | Plan target | Notes |
|---|---|---|
| `cmd/quay-distribution/main.go` | `cmd/quay/main.go` | Wrap in Cobra; existing init logic becomes `serve` subcommand body |
| `pkg/auth/jwk/` | `internal/auth/jwk/` | Adopt as-is |
| `pkg/auth/quay/` | `internal/registry/auth/` | Adopt as-is |
| `pkg/storage/drivers/quay_s3/` | `internal/storage/quay_s3/` | Adopt; extend for write paths |
| `pkg/storage/drivers/quay_akamai/` | `internal/storage/quay_akamai/` | Adopt as-is |
| `pkg/cache/` | `internal/cache/` | Adopt as-is |
| `pkg/metrics/` | `internal/metrics/` | Adopt as-is |
| `pkg/actionlogs/` | `internal/actionlogs/` | Adopt as-is |
| `pkg/config/` | `internal/config/` | Adopt; expand for mode presets, config-tool validators, Cobra flag integration |
| `pkg/database/` | `internal/dal/` | Major restructure per DAL design: pgx driver, sqlc generation, read-replica routing, encrypted fields, retry logic |
| `pkg/server/` | `internal/server/` | Adopt; add `/v1` wiring, owner-switch routing, Cobra integration |
| `pkg/server/middleware/` | `internal/registry/middleware/` | Adopt; add owner-switch-aware operation capture |
| `pkg/utils/` | `internal/utils/` | Adopt as-is |
| `internal/tracing/` | `internal/tracing/` | Adopt as-is (already in `internal/`) |

### 6.3 Go version

- **quay-distribution**: Go 1.24.0
- **Plan**: Go 1.23.x
- **Action**: Update plan to Go 1.24+. The existing code already works on 1.24, and Go 1.23 will be out of support before the rewrite ships.

### 6.4 CLI framework

- **quay-distribution**: raw `flag` package with CLI flags (`-config`, `-addr`, `-metrics-addr`, `-storage-driver`, `-tls-cert`, `-tls-key`, etc.)
- **Plan**: Cobra subcommands (`quay serve`, `quay install`, `quay config`, `quay migrate`, `quay worker`)
- **Action**: Add Cobra wrapper per OMR proposal. The existing `main.go` initialization logic (config loading, tracing init, server creation, graceful shutdown) becomes the body of the `serve` subcommand.

### 6.5 Storage driver completeness

- **quay-distribution**: read-only (PutContent/Writer/Move/Delete return `ErrUnsupportedMethod`)
- **Plan**: full read/write required for push operations
- **Action**: Implement write paths in S3 driver for blob upload. The upload state machine (`internal/registry/uploads/`) handles the coordination; the storage driver needs to support `Writer()` and `PutContent()`.

### 6.6 Database access pattern

- **quay-distribution**: global singleton (`GlobalContext`), `database/sql` + `lib/pq`
- **Plan**: request-scoped context, `pgx/v5` + `pgxpool`, read-replica routing, retry logic, encrypted field handling
- **Action**: Restructure per `data_access_layer_design.md`. Keep PR #74's sqlc pattern but switch the driver. Remove global singleton in favor of dependency injection.

## 7. What quay-distribution provides that the plan doesn't cover

These are implemented features not explicitly addressed in the plan sub-docs:

1. **Kinesis action log integration** (`pkg/actionlogs/`): distribution's `Listener` interface for writing action logs to Kinesis. Plan's `workers_inventory.md` covers background workers but doesn't explicitly call out the action log destination migration.

2. **AWS IP resolver** (`pkg/utils/ip_resolver.go`): loads AWS IP ranges JSON to determine if a client IP is in the same AWS region as the storage bucket, used by Akamai driver to bypass CDN for same-region traffic. Not mentioned in plan.

3. **Akamai EdgeAuth token generation** (`pkg/storage/drivers/quay_akamai/edgeauth.go`): full implementation of Akamai CDN URL signing with edge tokens. Plan's `storage_backend_inventory.md` lists Akamai but doesn't detail the EdgeAuth integration.

4. **Request path parser** (`pkg/utils/path_parser.go`): shared parsing for manifest/blob/layer paths, org/repo extraction from URIs. Useful utility not in plan.

5. **Config secret redaction** (`pkg/utils/logging.go`): prevents S3 keys, DB passwords, Akamai secrets from appearing in logs. Good security practice not explicitly required by plan.

6. **Metrics normalization** (`pkg/metrics/middleware.go`): groups similar HTTP paths (e.g., `/v2/{name}/manifests/{reference}`) to prevent metric cardinality explosion. Useful for plan's observability requirements.

**Recommendation**: Reference these in the relevant sub-plans as existing implementations to adopt.

## 8. What the plan covers that quay-distribution doesn't have

Major gaps that need new implementation:

| Gap | Plan reference | Scale |
|---|---|---|
| Push support (upload state machine) | `registryd_design.md` §uploads | 5-state FSM, hasher state serialization |
| `/v1` legacy registry routes | `registryd_design.md` §v1 | 26 routes |
| Schema1 manifest signing | `registryd_design.md` §schema1 | RS256 JWS signing/verification |
| Owner switch control plane | `switch_spec.md`, `switch_transport_design.md` | 3-level hierarchy, config polling |
| `/api/v1` REST API | `api_surface_inventory.md` | 268 routes (153 mutating) |
| Blueprint endpoints | `api_surface_inventory.md` | oauth, webhooks, keys, secscan, realtime, well-known, web (89 routes) |
| Worker processes | `workers_inventory.md` | 35 active workers across P0-P5 |
| Queue engine | `queue_contracts.md` | 9 queues, CAS claim semantics |
| Read-replica routing | `data_access_layer_design.md` §readreplica | Replica selection, quarantine, fallback |
| Encrypted field handling | `data_access_layer_design.md` §crypto, `fips_crypto_migration.md` | AES-CCM/CBC/Fernet compat |
| FIPS crypto wrappers | `fips_crypto_migration.md` | 14 primitives, 4-arch matrix |
| Cobra CLI (`quay serve/install/config/migrate`) | OMR proposal, `quay_rewrite.md` §4 | CLI framework |
| SQLite support (mirror mode) | `quay_rewrite.md` §4.1 | Embedded DB |
| Quadlet generation | OMR proposal | Systemd unit files for containerized deploy |
| Config-tool validators | `config_tool_evolution.md` | Field group validation |
| 11 additional storage drivers | `storage_backend_inventory.md` | Azure, Swift, GCS, Rados, CloudFront, CloudFlare, local, etc. |
| Canary selectors | `cutover_matrix.md` | org/repo/user/percent scoping |
| Contract test harness | `test_strategy.md` | Python-oracle vs Go-candidate |
| Performance budget enforcement | `performance_budget.md` | p50/p99 latency budgets |

## 9. Component-level adoption guidance

### 9.1 Adopt as-is (move to `internal/`, update imports)

These packages are production-quality and align with the plan:

- `pkg/auth/jwk/` → `internal/auth/jwk/`
- `pkg/auth/quay/` → `internal/registry/auth/`
- `pkg/storage/drivers/quay_s3/` → `internal/storage/quay_s3/`
- `pkg/storage/drivers/quay_akamai/` → `internal/storage/quay_akamai/`
- `pkg/cache/` → `internal/cache/`
- `pkg/metrics/` → `internal/metrics/`
- `pkg/actionlogs/` → `internal/actionlogs/`
- `pkg/utils/ip_resolver.go` → `internal/utils/`
- `pkg/utils/path_parser.go` → `internal/utils/`
- `pkg/utils/logging.go` → `internal/utils/`
- `pkg/utils/context.go` → `internal/utils/`
- `internal/tracing/` → `internal/tracing/`
- `pkg/server/middleware/registry.go` → `internal/registry/middleware/`
- OpenShift deployment template
- Dockerfile (UBI 10 base)
- CI workflows (lint, test, build)
- Dependabot config
- Gitleaks config

### 9.2 Adopt with modifications

- **`pkg/config/`** → `internal/config/`: expand for mode presets (mirror/standalone/full), absorb config-tool field group validators, add Cobra flag integration, add SQLite/local-only config paths for mirror mode
- **`pkg/database/`** → `internal/dal/`: restructure per DAL design. Adopt PR #74's sqlc pattern. Switch driver from `database/sql`+`lib/pq` to `pgx/v5`+`pgxpool`. Remove global singleton. Add read-replica routing, encrypted field handling, retry logic, `state_id` CAS behavior, bcrypt parity, delete cascade semantics.
- **`pkg/server/`** → `internal/server/`: add Cobra subcommand integration, add `/v1` route wiring, add owner-switch-aware routing middleware, add mode-preset-aware server initialization

### 9.3 Do not adopt (needs rework or is out of scope)

- **PR #13 rate limiting**: in-process-only approach is architecturally insufficient per reviewer feedback. Needs Redis-backed shared state for multi-instance. Consider `chi/httprate` with Redis backend. Track for later integration.
- **PR #1 secscan rewrite**: stale since Sep 2025 (5 months). Contains original prototyping WIP commits mixed with secscan work. Extract any useful secscan integration patterns but don't merge the branch.
- **gorilla/mux router**: archived/maintenance-only. Replace with `chi/v5` during integration.
- **Global singleton pattern** (`database.GlobalContext`): replace with dependency injection per DAL design.

## 10. Recommended plan updates

After team review, the following changes should be made to the master plan and sub-plans:

### 10.1 Master plan (`quay_rewrite.md`)

- Add `quay/quay-distribution` to the document map as "Existing Go implementation (prototype)" with link
- Update Go version from 1.23.x to 1.24+
- Note that the `/v2` read path, JWT auth, S3/Akamai storage drivers, Redis caching, metrics, tracing, and config loading have working implementations to build on
- Note that push support, `/v1` routes, Schema1 signing, upload state machine, and all non-registry surfaces need new implementation

### 10.2 `registryd_design.md`

- Reference quay-distribution's auth controller as the starting implementation for `internal/registry/auth/`
- Reference quay-distribution's S3 and Akamai drivers as the starting implementation for `internal/registry/storage/`
- Note that write paths (PutContent, Writer) need to be added to existing drivers
- Note the existing distribution `Listener` integration for action logs

### 10.3 `data_access_layer_design.md`

- Reference PR #74 as validation of the sqlc approach
- Note the three-layer pattern (SQL → generated → domain) has been prototyped and works
- Document the `database/sql` → `pgx/v5` driver switch needed
- Document the global singleton → dependency injection migration

### 10.4 `go_module_strategy.md`

- Update Go version to 1.24+
- Add section on integrating code from quay-distribution (module path change, pkg → internal rename, import updates)
- Reference existing CI workflows as a starting point for the main repo's Go CI

### 10.5 `storage_backend_inventory.md`

- Mark S3Storage and AkamaiS3Storage as "prototype exists" in the tracker
- Note read-only limitation and write path gap

### 10.6 `implementation_backlog.md`

- Add integration of quay-distribution as a task in WS3 (registry migration)
- Add PR #74 sqlc adoption as a task in WS8 (data layer)
- Consider adding rate limiting migration as a backlog item (not currently tracked)

### 10.7 `redis_usage_inventory.md`

- Reference quay-distribution's cache implementation as a starting point for the Go cache layer

### 10.8 New sub-plan considerations

- **Rate limiting migration**: not currently addressed in any sub-plan. quay-distribution PR #13 and reviewer feedback highlight this gap. Decide: keep rate limiting in nginx during coexistence (plan's current implicit approach) or migrate to Go middleware with Redis backend.
- **Action log destination migration**: Kinesis integration exists in quay-distribution but isn't called out in the plan's worker/queue inventories. Verify coverage.

## 11. Risk assessment

### 11.1 Low risk (well-aligned)

- Distribution v3 integration approach matches
- JWT auth approach matches
- sqlc approach validated by PR #74
- Prometheus/OpenTelemetry stack matches
- UBI 10 container image approach matches

### 11.2 Medium risk (reconcilable)

- gorilla/mux → chi migration (mechanical, similar API, but touches all route registrations)
- `database/sql` → pgx migration (driver swap, connection pool behavior changes)
- `pkg/` → `internal/` rename (mechanical, but large diff)
- Go 1.23 → 1.24 version bump (plan update needed, should be uncontroversial)
- Global singleton removal (requires dependency injection refactor in server initialization)

### 11.3 Higher risk (needs discussion)

- **Module consolidation**: merging quay-distribution into the main quay repo means coordinating with the existing Python CI, pre-commit hooks, and build system. The Go module at the quay repo root will coexist with Python source. This is the plan's intended approach (`go_module_strategy.md`) but hasn't been tested yet.
- **Engineer on leave**: primary contributor (Syed, 44/64 commits) is on leave. Knowledge transfer gaps may exist for the S3 driver internals, config translation logic, and action log integration. The code is readable but undocumented in some areas.
- **Stale PRs**: PR #1 (secscan, 5 months stale) and PR #13 (rate limiting, 2 months stale with changes requested) may need to be closed and restarted rather than rebased.
- **PR #51 vs #74 conflict**: both modify `models.go` with incompatible approaches. PR #74 (sqlc) supersedes PR #51 (hand-written models). Need to decide and close one.

## 12. Integration sequence

Recommended order for bringing quay-distribution into the main repo:

1. **Initialize Go module** in main quay repo (`go.mod`, `go.sum`, CI checks) per `go_module_strategy.md`
2. **Port `internal/tracing/`** first (no dependencies on other packages, validates Go module + CI)
3. **Port `pkg/utils/`** → `internal/utils/` (shared utilities, low coupling)
4. **Port `pkg/cache/`** → `internal/cache/` (self-contained, depends only on go-redis)
5. **Port `pkg/metrics/`** → `internal/metrics/` (self-contained, depends only on prometheus)
6. **Port `pkg/config/`** → `internal/config/` (Quay YAML loading, add mode presets)
7. **Port `pkg/database/`** → `internal/dal/` with PR #74's sqlc approach, switching to pgx
8. **Port `pkg/auth/`** → `internal/auth/` + `internal/registry/auth/`
9. **Port `pkg/storage/drivers/`** → `internal/storage/`
10. **Port `pkg/actionlogs/`** → `internal/actionlogs/`
11. **Port `pkg/server/`** → `internal/server/` with Cobra CLI wrapper
12. **Add write paths** to storage drivers and implement upload state machine
13. **Add `/v1` routes** and Schema1 signing
14. **Add owner switch control plane**

Steps 1-6 can be done without blocking on any G8-G15 gate approvals. Steps 7+ depend on DAL design (G8) and registryd architecture (G11) approval.
