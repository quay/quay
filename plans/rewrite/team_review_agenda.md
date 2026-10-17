# Quay Go Rewrite - Team Review Meeting

Date: 2026-02-12
Duration: 60 minutes
PR: quay/quay#5011 (branch: `feature/go-plan`)

---

## Meeting format

This meeting is split into two halves:

- **First 30 minutes**: Independent review using Claude Code (Opus 4.6 1M context). Check out the branch, use the starter prompt below, read the plans, ask questions, and prepare your feedback.
- **Second 30 minutes**: Live group discussion. We'll go through unresolved questions, debate the high-risk areas, assign workstream owners, and agree on next steps.

---

## Setup instructions

### 1. Check out the branch

```bash
cd /path/to/quay
git fetch origin
git checkout feature/go-plan
```

### 2. Start Claude Code

Make sure you're using Opus 4.6 with 1M context. From the repo root:

```bash
claude
```

### 3. Paste the starter prompt

Copy and paste the following prompt to kick off your review session:

---

```
I'm reviewing a plan to rewrite Quay's backend from Python to Go. The plan is on
this branch in plans/rewrite/. Start by reading the master plan at
plans/rewrite/quay_rewrite.md, then read these key documents:

- plans/rewrite/architecture_diagrams.md (7 Mermaid architecture diagrams)
- plans/rewrite/quay_distribution_reconciliation.md (analysis of existing Go prototype)

Then based on my area of expertise (I'll tell you below), read the relevant sub-plans
and give me:

1. A summary of what's being proposed and how it affects my area
2. Any gaps, risks, or concerns you see
3. Questions I should raise in the team discussion
4. If I disagree with anything or want to propose changes, help me draft the edits

My area: [REPLACE WITH YOUR AREA - e.g., "registry and storage",
"database and data layer", "auth and security", "workers and queues",
"deployment and CI", "FIPS and crypto", "testing", or "general/all areas"]
```

---

### 4. Follow-up questions to ask Claude

After the initial review, here are useful follow-ups depending on what you find:

- "Read `plans/rewrite/[specific-sub-plan].md` and tell me if the approach makes sense for [specific concern]"
- "Compare what `quay/quay-distribution` has implemented (see `quay_distribution_reconciliation.md`) against what the plan proposes for [area]. Are there conflicts?"
- "I think [X] is wrong in the plan. Help me write an alternative proposal."
- "What does the plan say about [specific topic]? Search across all the sub-plans."
- "Read `plans/rewrite/generated/[tracker].csv` and summarize the status for [area]."
- "Help me draft a PR comment explaining my concern about [topic]."

---

## How to provide feedback

### Questions (things you want to discuss live)

Post questions as comments on [PR #5011](https://github.com/quay/quay/pull/5011). Prefix your comment with **`[QUESTION]`** so we can collect them for the live discussion. Example:

> **[QUESTION]** The upload hasher state pinning strategy (registryd_design.md) assumes we can route by upload UUID during M2-M3. How does this interact with the nginx prefix-based routing in switch_spec.md? Does nginx need to inspect the request body or can this be done at the path level?

### Proposed changes (edits to the plan)

If you want to change something in the plan:

1. Create a branch off `feature/go-plan`:
   ```bash
   git checkout -b feature/go-plan-<your-name> feature/go-plan
   ```
2. Make your edits (Claude Code can help you write them)
3. Push and open a PR targeting `feature/go-plan` (not `master`):
   ```bash
   git push origin feature/go-plan-<your-name>
   gh pr create --base feature/go-plan --title "plan: <short description of your change>"
   ```

These PRs will be reviewed and merged into the plan branch, which automatically updates PR #5011.

### Quick comments (agreement, minor notes, thumbs up/down)

Use inline PR review comments on specific lines in PR #5011. These don't need the `[QUESTION]` prefix.

---

## Key documents by area

All docs are under `plans/rewrite/`. Start with the master plan, then go to your area.

| Area | Start here | Then read |
|------|-----------|-----------|
| Everyone | `quay_rewrite.md`, `architecture_diagrams.md` | `quay_distribution_reconciliation.md` |
| Registry | `registryd_design.md` | `storage_backend_inventory.md`, `generated/route_family_cutover_sequence.md` |
| Data layer | `data_access_layer_design.md` | `db_migration_policy.md`, `go_module_strategy.md` |
| Workers/queues | `workers_inventory.md` | `queue_contracts.md`, `queue_cutover_dependencies.md`, `generated/worker_phase_sequence.md` |
| Auth/security | `auth_backend_inventory.md` | `fips_crypto_migration.md`, `tls_security_posture.md` |
| Deployment | `deployment_architecture.md` | `image_strategy.md`, `config_tool_evolution.md` |
| Testing | `test_strategy.md` | `test_implementation_plan.md`, `performance_budget.md` |
| Migration controls | `switch_spec.md` | `switch_transport_design.md`, `cutover_matrix.md` |

---

## Live discussion agenda (second 30 minutes)

### 1. Collect unresolved questions (5 min)

Gather `[QUESTION]` comments from the PR. Triage into discuss-now vs. follow-up.

### 2. Architecture and approach (5 min)

> We're replacing the entire Python backend with a single Go binary. Three mode presets (mirror/standalone/full), capability-based incremental cutover with instant rollback, nginx routing during coexistence. An existing Go prototype (`quay-distribution`) gives us a working `/v2` pull path and 2 storage drivers to build on.

Key decision to confirm: **mirror-first** as the starting implementation track.

### 3. High-risk areas (10 min)

Walk through the top risks and get gut reactions:

1. **Upload hasher state** - pickle serialization breaks cross-runtime uploads; plan pins by UUID during M2-M3
2. **FIPS** - 14 crypto primitives need Go equivalents; AES-CCM, SHA-1 for Swift/CloudFront, CRAM-MD5 for SMTP are the hard ones
3. **Ordered queue** - build manager requires `ordering_required=True`; Go must preserve this exactly
4. **3 missing queues** - not cleaned up on namespace deletion; fix in Go or preserve the bug?
5. **Alembic bridge** - Python migration tooling sticks around until M5+
6. **Multi-arch FIPS** - 4 architectures all need GOFIPS140 validation

### 4. Workstream ownership (5 min)

13 workstreams (WS0-WS12). 6 are unblocked and can start now. Assign names.

| WS | Scope | Unblocked? |
|----|-------|------------|
| WS0 | Program control, gates | Yes |
| WS1 | Contract test harness | Yes |
| WS2 | Ownership switch control plane | Yes |
| WS3 | Registry (`/v2` + `/v1`, 45 routes) | Blocked on G11 |
| WS4 | API + blueprints (357 routes) | Blocked on G8 |
| WS5 | Workers + build manager (35 procs) | Blocked on G8 |
| WS6 | Queue engine + payloads (9 queues) | Yes |
| WS7 | Auth + identity (6 providers) | Blocked on G14 |
| WS8 | Data layer + schema | Blocked on G8 |
| WS9 | FIPS, TLS, crypto (14 primitives) | Blocked on G9 |
| WS10 | Runtime support + Redis | Blocked on G12 |
| WS11 | Deployment + images | Blocked on G13 |
| WS12 | Route auth verification | Yes |

### 5. Next steps (5 min)

1. Assign reviewers for blocked gates G8-G15 (target: approved within 2 weeks)
2. Create Jira epics for WS0-WS12
3. Start mirror mode (MM) implementation - init Go module, scaffold `cmd/quay/`
4. Schedule deep-dives: upload hasher state, FIPS crypto, build manager queue, DAL architecture
5. Feedback deadline: EOW on PR #5011, then plan is baselined

---

## Presenter notes

Detailed talking points for each agenda section are below. These are for the meeting facilitator only.

---

### Presenter note: Context (if needed for the live discussion)

> We're proposing a full rewrite of Quay's backend from Python to Go. Not a partial port, not a sidecar - a complete replacement of the Python runtime. The plan covers every API endpoint, every background worker, and every queue.

- **Why Go**: Today's Quay image ships Python, Node, nginx, supervisord, memcached, dnsmasq, skopeo. The Go target is a single statically-linked binary.
- **Why now**: The OMR team independently proposed unifying mirror-registry, quay-distribution-main, and config-tool into a single Go CLI. That proposal and this plan have been reconciled.
- **Scope**: 413 route method rows, 36 supervisor programs, 9 queues, 13 storage drivers, 14 crypto primitives. Fully mapped from source code, not estimated.
- **Existing work**: `quay/quay-distribution` has a working `/v2` read path with JWT auth, S3+Akamai drivers, Redis cache, metrics, tracing (64 commits, 60 Go files). See `quay_distribution_reconciliation.md`.
- **Hard constraints**: zero API regressions, `/v1` stays, incremental cutover, FIPS support, DB invariants preserved.

### Presenter note: Architecture details

**Mode presets**:

| Mode | DB | Storage | Auth | Cache | TLS | Use case |
|------|-----|---------|------|-------|-----|----------|
| `mirror` | SQLite | Local FS | Anon | In-memory | Self-signed auto | Air-gapped mirrors, dev |
| `standalone` | PostgreSQL | S3 or local | DB auth | Redis | User-provided | Single-node production |
| `full` | PostgreSQL | S3 + CDN | LDAP/OIDC | Redis | Required | Enterprise multi-node |

**Dependency choices**: distribution/v3, pgx/v5 + sqlc (not GORM/ent), chi/v5 (not gorilla/mux which is archived), golang-jwt/v5, Alembic stays until M5+.

**quay-distribution divergences to resolve**: gorilla/mux → chi, database/sql → pgx, pkg/ → internal/, Go 1.24 vs plan's 1.23.

### Presenter note: Migration mechanics

- Capability-based cutover, not big-bang. One owner per capability (`python`|`go`).
- Switch hierarchy: route-method → capability → family → global default (`python`).
- Transport: config-provider polling, 5-15s interval, <30s propagation SLO.
- Rollback = config change, not redeploy. Emergency: `MIGRATION_FORCE_PYTHON=true`.
- nginx routes to Python or Go upstream during coexistence (existing infra, zero new proxy code).
- Quality gates per capability: contract parity, perf budget, auth parity, FIPS, observability, runbook.

### Presenter note: Milestones

| Milestone | What | Scale |
|-----------|------|-------|
| MM (parallel) | Mirror mode: `quay serve --mode=mirror`, validates Go stack | `/v2` only, no Python |
| M0 | Planning gate: all plans approved, Go scaffold green | G0-G15 |
| M1 | Switch infra, canary, rollback validation | Control plane |
| M2 | `/v2` + `/v1` parity | 45 routes |
| M3 | `/api/v1` + blueprints | 357 routes |
| M4 | Workers P0-P5 + build manager | 35 processes |
| M5 | Python deactivation, nginx removed, Quadlet for all modes | Full cutover |

G0-G7 ready. G8-G15 blocked pending architectural approval.

### Presenter note: Risk details

1. **Upload hasher state**: Python pickles SHA state into `BlobUpload.sha_state`. Go can't read pickle. Pin uploads by UUID during M2-M3, JSON/protobuf cross-runtime format post-M4.
2. **FIPS**: AES-CCM (no vetted Go CCM), Swift TempURL HMAC-SHA1 (disallowed in FIPS-strict), CloudFront RSA+SHA1, CRAM-MD5 (MD5 blocked in FIPS), AES key derivation via `itertools.cycle` (not a real KDF, must reproduce byte-for-byte).
3. **Ordered queue**: build manager `ordering_required=True`. P5 (last phase) for a reason.
4. **Missing queues**: `proxy_cache_blob_queue`, `secscan_notification_queue`, `export_action_logs_queue` not in `all_queues`. Namespace deletion doesn't clean them. Fix in Go?
5. **Alembic**: Python migration tool stays until M5+. Can't remove Peewee from repo until replaced.
6. **Multi-arch FIPS**: x86_64, aarch64, ppc64le, s390x all need GOFIPS140 smoke tests.

### Presenter note: Workstream details

**Can start now**: WS0 (program control), WS1 (test harness - Python oracle first), WS2 (switch control plane), WS6 (queue contracts), WS12 (route auth verification), MM (mirror mode).

**Most blocking gate**: G8 (DAL architecture) - blocks WS4, WS5, WS8.

**Largest workstream**: WS4 (268 api-v1 routes, 153 mutating, plus 89 blueprint routes).

**Hardest individual items**: P4 GC workers (global lock semantics), P5 builder (ordered queue), FIPS crypto (14 primitives, 4 architectures).

---

## Reference numbers

- Total route method rows: 413 (191 mutating)
- Route families: 12 (registry-v2, registry-v1, api-v1, oauth1, oauth2, webhooks, keys, secscan, realtime, well-known, web, other)
- Supervisor programs: 36 (35 active + 1 retired)
- Worker rollout phases: P0-P5 (7 service support, 11 schedulers, 7 queue workers, 6 complex, 3 GC, 1 builder)
- Queues: 9 (3 not in `all_queues`)
- Storage drivers: 13
- Crypto primitives: 14
- Auth providers: 6
- Program gates: 16 (G0-G7 ready, G8-G15 blocked)
- Approved decisions: 5 (D-001 through D-005)
- Workstreams: 13 (WS0-WS12)
- Sub-plan documents: 40+
- Target architectures: 4 (x86_64, aarch64, ppc64le, s390x)
