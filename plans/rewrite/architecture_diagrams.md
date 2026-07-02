# Quay Rewrite Architecture Diagrams

Status: Draft for team review
Generated: 2026-02-11

---

## 1. System Architecture Overview

Current Python architecture mapped to target Go architecture.

```mermaid
graph TB
    subgraph current["Current Python Architecture"]
        direction TB
        nginx_py["nginx<br/>(TLS, routing, rate limiting)"]

        subgraph gunicorn["gunicorn Process Groups"]
            g_reg["gunicorn-registry<br/>(Flask, /v1 + /v2)"]
            g_web["gunicorn-web<br/>(Flask, /api/v1 + UI)"]
            g_sec["gunicorn-secscan<br/>(Flask, /secscan)"]
        end

        subgraph supervisord["supervisord (36 programs)"]
            svc["Service Support<br/>dnsmasq, memcache,<br/>pushgateway, nginx"]
            p1["P1: Schedulers (11)<br/>buildlogsarchiver,<br/>globalpromstats,<br/>servicekey, etc."]
            p2["P2: Queue Workers (7)<br/>notificationworker,<br/>storagereplication,<br/>chunkcleanupworker, etc."]
            p3["P3: Complex Workers (6)<br/>repomirrorworker,<br/>securityworker,<br/>teamsyncworker, etc."]
            p4["P4: GC Workers (3)<br/>gcworker,<br/>namespacegcworker,<br/>repositorygcworker"]
            p5["P5: Build Manager (1)<br/>builder<br/>(ordered queue)"]
        end

        peewee["Peewee ORM<br/>(data/database.py)"]

        nginx_py --> g_reg & g_web & g_sec
        g_reg & g_web & g_sec --> peewee
        p2 & p3 & p4 & p5 --> peewee
    end

    subgraph target["Target Go Architecture"]
        direction TB
        quay_cli["quay CLI<br/>(single Go binary)"]

        subgraph modes["Serving Mode Presets"]
            mirror["mirror<br/>SQLite, local FS,<br/>anon, in-memory cache,<br/>self-signed TLS"]
            standalone["standalone<br/>PostgreSQL, S3/local,<br/>DB auth, Redis,<br/>user-provided TLS"]
            full["full<br/>PostgreSQL, S3+CDN,<br/>LDAP/OIDC/OAuth,<br/>Redis, required TLS"]
        end

        subgraph go_svc["Go Services"]
            registryd["registryd<br/>(/v1 + /v2)<br/>distribution/v3"]
            api_svc["api-service<br/>(/api/v1 + blueprints)"]
            workers_go["worker-*<br/>(goroutines in mirror,<br/>separate procs in full)"]
        end

        subgraph go_dal["Go Data Access Layer"]
            pgx["pgx/v5 + pgxpool"]
            sqlc["sqlc generated queries"]
            dal_repo["internal/dal/repositories/"]
        end

        quay_cli --> modes
        quay_cli --> go_svc
        go_svc --> go_dal
    end

    subgraph shared["Shared Infrastructure"]
        pg[("PostgreSQL")]
        redis[("Redis")]
        s3[("Object Storage<br/>S3/Azure/Swift/GCS/Local")]
    end

    peewee --> pg
    go_dal --> pg
    current --> redis
    target --> redis
    current --> s3
    target --> s3

    style current fill:#fff3e0,stroke:#e65100
    style target fill:#e3f2fd,stroke:#1565c0
    style shared fill:#f3e5f5,stroke:#6a1b9a
```

> **Key decisions**: Go uses pgx/v5 + sqlc (not GORM/ent). Alembic remains migration authority until M5+. Distribution v3 provides the registry core. Single binary with subcommands replaces supervisord + 3 gunicorn groups.

---

## 2. Migration Topology (Transition State)

Containerized deployment during Python/Go coexistence with deployment profiles.

```mermaid
graph TB
    subgraph transition["Transition State: Python + Go Coexistence"]
        client["Container Client<br/>(podman/docker/skopeo)"]

        nginx["nginx<br/>(front door)<br/>server-base.conf.jnj<br/>---<br/>Routes by URL prefix<br/>Rate limiting, buffering,<br/>timeout tuning"]

        client --> nginx

        subgraph python_upstream["Python Upstream (legacy)"]
            py_reg["registry_app_server<br/>(gunicorn-registry)"]
            py_web["web_app_server<br/>(gunicorn-web)"]
            py_sec["secscan_app_server<br/>(gunicorn-secscan)"]
            py_workers["Python Workers<br/>(supervisord)"]
        end

        subgraph go_upstream["Go Upstream (new)"]
            go_reg["registryd<br/>(quay serve registryd)"]
            go_api["api-service<br/>(quay serve api-service)"]
            go_workers["Go Workers<br/>(quay worker *)"]
        end

        subgraph control["Switch Control Plane"]
            config_provider["Config Provider<br/>(config.yaml migration section)"]
            switch_lib["Owner Decision Library<br/>Route: method → cap → family → global<br/>Worker: WORKER_OWNER_<PROGRAM>"]
            canary["Canary Selectors<br/>org / repo / user / percent"]
            kill["Emergency Kill Switch<br/>MIGRATION_FORCE_PYTHON=true"]

            config_provider -->|"poll 5-15s<br/>SLO <30s"| switch_lib
            switch_lib --> canary
        end

        nginx -->|"owner=python"| python_upstream
        nginx -->|"owner=go"| go_upstream
        switch_lib -.->|"routing decision"| nginx
    end

    subgraph profiles["Deployment Profiles (quay install)"]
        direction LR

        subgraph mirror_profile["mirror"]
            m_container["Single Container<br/>quay serve --mode=mirror"]
            m_sqlite[("SQLite")]
            m_local[("Local FS")]
            m_container --> m_sqlite & m_local
        end

        subgraph standalone_profile["standalone"]
            s_app["App Container<br/>quay serve --mode=standalone"]
            s_redis[("Redis")]
            s_pg[("PostgreSQL")]
            s_app --> s_redis & s_pg
        end

        subgraph ha_profile["full / HA"]
            ha_app["App Container(s)<br/>quay serve --mode=full"]
            ha_redis[("Redis<br/>(external)")]
            ha_pg[("PostgreSQL<br/>(external)")]
            ha_s3[("S3<br/>(external)")]
            ha_app --> ha_redis & ha_pg & ha_s3
        end
    end

    subgraph data_tier["Shared Data Tier (transition)"]
        pg_shared[("PostgreSQL<br/>Alembic-managed schema")]
        redis_shared[("Redis<br/>model cache, real-time,<br/>build logs, rate limiting")]
        storage_shared[("Object Storage")]
    end

    python_upstream --> data_tier
    go_upstream --> data_tier

    style python_upstream fill:#fff3e0,stroke:#e65100
    style go_upstream fill:#e3f2fd,stroke:#1565c0
    style control fill:#fce4ec,stroke:#c62828
    style profiles fill:#e8f5e9,stroke:#2e7d32
```

> **Risk note**: During coexistence, both Python and Go read/write the same PostgreSQL database. The expand-migrate-contract pattern governs schema evolution. No non-additive DDL without an approved exception per `db_migration_policy.md`.

---

## 3. Capability Cutover Flow

Lifecycle of migrating one capability from Python to Go ownership.

```mermaid
flowchart TD
    start(["Capability X<br/>owner = python"]) --> implement["Implement Go handler<br/>behind disabled switch"]

    implement --> contract["Run Contract Tests<br/>(Python-oracle vs Go-candidate)"]

    contract -->|FAIL| fix["Fix Go implementation"]
    fix --> contract

    contract -->|PASS| perf["Performance Budget Check<br/>(p50/p99 latency, throughput,<br/>error rate within budget)"]

    perf -->|FAIL| optimize["Optimize Go handler"]
    optimize --> perf

    perf -->|PASS| canary_start["Enable Canary<br/>ROUTE_CANARY_ORGS=test-org<br/>ROUTE_CANARY_PERCENT=5"]

    canary_start --> canary_monitor["Monitor Canary<br/>(error rate, latency, correctness)"]

    canary_monitor -->|"Issues detected"| rollback_canary["Rollback Canary<br/>Set owner=python<br/>(<30s propagation)"]
    rollback_canary --> fix

    canary_monitor -->|"Burn-in passes"| expand["Expand Traffic<br/>10% → 25% → 50% → 100%"]

    expand --> full_go["Set Capability Owner = go<br/>via switch hierarchy"]

    full_go --> stability["Stability Window<br/>(Python fallback available)"]

    stability --> disable_py["Disable Python Handler<br/>(Python remains emergency fallback)"]

    disable_py --> done(["Capability X<br/>owner = go"])

    subgraph switch_resolution["Switch Resolution (highest → lowest)"]
        direction LR
        s1["Route-method<br/>ROUTE_OWNER_ROUTE_0324"]
        s2["Capability<br/>ROUTE_OWNER_CAP_V2_PULL"]
        s3["Family<br/>ROUTE_OWNER_FAMILY_REGISTRY_V2"]
        s4["Global default<br/>(python)"]
        s1 --> s2 --> s3 --> s4
    end

    subgraph transport["Switch Transport"]
        direction LR
        config["config.yaml<br/>migration section"]
        poll["Runtime poll<br/>5-15s interval"]
        snapshot["Snapshot<br/>{version, updated_at,<br/>owner_map}"]
        fallback["Parse failure →<br/>last-known-good<br/>Hard failure →<br/>python"]
        config --> poll --> snapshot --> fallback
    end

    subgraph gates["Quality Gates (each capability)"]
        g1["Contract parity ✓"]
        g2["Unit/integration/E2E ✓"]
        g3["Performance budget ✓"]
        g4["Auth parity ✓"]
        g5["DB/replica compat ✓"]
        g6["FIPS compat ✓"]
        g7["Observability parity ✓"]
        g8["Runbook + rollback doc ✓"]
    end

    style start fill:#fff3e0,stroke:#e65100
    style done fill:#e3f2fd,stroke:#1565c0
    style rollback_canary fill:#ffcdd2,stroke:#c62828
    style switch_resolution fill:#f3e5f5,stroke:#6a1b9a
    style transport fill:#e0f7fa,stroke:#00695c
    style gates fill:#e8f5e9,stroke:#2e7d32
```

> **Rollback is a single config change** (no redeploy). Set owner back to `python`, wait <30s for propagation, confirm via owner-decision metrics. Emergency: `MIGRATION_FORCE_PYTHON=true` forces all capabilities back to Python.

---

## 4. Milestone Dependency Graph

```mermaid
graph TD
    subgraph parallel["Parallel Track"]
        MM["MM: Mirror Mode<br/>---<br/>quay serve --mode=mirror<br/>quay install --profile=mirror<br/>quay config validate<br/>quay migrate<br/>/v2 contract tests pass<br/>---<br/>Validates shared infra"]
    end

    subgraph gates_blocked["Blocked Gates (G8-G15)"]
        G8["G8: DAL approved"]
        G9["G9: FIPS/crypto approved"]
        G10["G10: Storage approved"]
        G11["G11: Registryd approved"]
        G12["G12: Redis approved"]
        G13["G13: Deploy/image/config/TLS"]
        G14["G14: Auth + notifications"]
        G15["G15: Perf baselines"]
    end

    subgraph gates_ready["Ready Gates (G0-G7)"]
        G0["G0: Inventory complete ✅"]
        G1["G1: Switch design complete ✅"]
        G2["G2: Decisions approved ✅"]
        G3["G3: Verification anchored ✅"]
        G4["G4: Test rollout defined ✅"]
        G5["G5: Runtime waves defined ✅"]
        G6["G6: Playbooks complete ✅"]
        G7["G7: Ops tooling dispositions ⚠️"]
    end

    M0["M0: Contracts & Inventory Gate<br/>---<br/>All inventories reviewed<br/>Go scaffold + CI green<br/>Contract fixtures established<br/>Auth verification complete<br/>---<br/>Gates: G0-G15"]

    M1["M1: Edge Routing & Controls<br/>---<br/>Capability ownership switches<br/>Canary by org/repo/capability<br/>Instant rollback validated<br/>nginx config gen for Go upstream"]

    M2["M2: Registry Migration<br/>---<br/>/v2 parity (R1: 19 routes)<br/>/v1 parity (R2: 26 routes)<br/>Python registry disable per-cap"]

    M3["M3: Non-Registry API<br/>---<br/>/api/v1 (R5: 268 routes)<br/>OAuth (R3-R4: 11 routes)<br/>Webhooks, keys, secscan,<br/>realtime, well-known, web<br/>(R6-R12: 89 routes)"]

    M4["M4: Workers & Build Manager<br/>---<br/>P1: 11 schedulers<br/>P2: 7 queue workers<br/>P3: 6 complex workers<br/>P4: 3 GC workers<br/>P5: 1 build manager"]

    M5["M5: Python Deactivation<br/>---<br/>All capabilities → Go<br/>Python emergency-only<br/>Quadlet profiles for all modes<br/>nginx removed from topology<br/>quay serve = container entrypoint"]

    MM -->|"validates Go scaffold,<br/>dist v3, local storage,<br/>TLS, config"| M0

    gates_ready --> M0
    gates_blocked --> M0

    M0 --> M1
    M1 --> M2
    M2 --> M3
    M3 --> M4
    M4 --> M5

    MM -->|"feeds /v2 handlers,<br/>storage drivers"| M2

    style MM fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style M0 fill:#ffecb3,stroke:#f57f17,stroke-width:2px
    style M1 fill:#e1f5fe,stroke:#0277bd
    style M2 fill:#e1f5fe,stroke:#0277bd
    style M3 fill:#e1f5fe,stroke:#0277bd
    style M4 fill:#e1f5fe,stroke:#0277bd
    style M5 fill:#e1f5fe,stroke:#0277bd,stroke-width:3px
    style gates_ready fill:#e8f5e9,stroke:#2e7d32
    style gates_blocked fill:#ffcdd2,stroke:#c62828
    style parallel fill:#c8e6c9,stroke:#2e7d32
```

> **MM runs in parallel** and does not block M1-M5. It validates the Go binary, CI pipeline, distribution v3, local storage, TLS, and config subsystems. Results feed into M0 readiness and M2 registry work. **8 gates (G8-G15) are currently blocked** pending architectural approval.

---

## 5. Data Flow: Registry Push/Pull

### 5a. Registry V2 Pull (Manifest + Blob)

```mermaid
sequenceDiagram
    participant C as Container Client
    participant N as nginx
    participant SW as Switch Library
    participant PY as Python Registry<br/>(gunicorn-registry)
    participant GO as Go registryd<br/>(distribution/v3)
    participant AUTH as Auth Service<br/>(/v2/auth)
    participant DB as PostgreSQL
    participant S3 as Object Storage

    C->>N: GET /v2/auth?service=&scope=repository:ns/repo:pull
    N->>AUTH: proxy to auth handler
    AUTH->>DB: validate credentials, check permissions
    DB-->>AUTH: user + scopes
    AUTH-->>N: JWT token (signed, scoped)
    N-->>C: 200 {token: "eyJ..."}

    C->>N: GET /v2/ns/repo/manifests/tag
    N->>SW: resolve owner for /v2 manifests GET

    alt owner = python
        SW-->>N: route to Python
        N->>PY: GET /v2/ns/repo/manifests/tag
        PY->>DB: lookup manifest by tag
        DB-->>PY: manifest row + digest
        PY->>S3: fetch manifest blob
        S3-->>PY: manifest JSON
        PY-->>N: 200 manifest + Content-Type + Docker-Content-Digest
    else owner = go
        SW-->>N: route to Go
        N->>GO: GET /v2/ns/repo/manifests/tag
        GO->>DB: lookup manifest by tag (pgx/sqlc)
        DB-->>GO: manifest row + digest
        GO->>S3: fetch manifest blob (distribution/v3 driver)
        S3-->>GO: manifest JSON
        GO-->>N: 200 manifest + Content-Type + Docker-Content-Digest
    end

    N-->>C: manifest response

    C->>N: GET /v2/ns/repo/blobs/sha256:abc...
    Note over N,S3: Same owner-switch flow for blob layer downloads
    N-->>C: 200 blob data (or 307 redirect to storage)
```

### 5b. Registry V2 Push (with Upload State Machine)

```mermaid
sequenceDiagram
    participant C as Container Client
    participant GO as Go registryd
    participant SM as Upload State Machine
    participant DB as PostgreSQL
    participant S3 as Object Storage

    Note over SM: 5 States from registryd_design.md

    C->>GO: POST /v2/ns/repo/blobs/uploads/
    GO->>SM: State 1: Start Upload
    SM->>DB: create BlobUpload session
    DB-->>SM: session {id, offset=0}
    SM-->>GO: session ID + location
    GO-->>C: 202 Location: /v2/ns/repo/blobs/uploads/<uuid>

    loop Chunked Upload
        C->>GO: PATCH /v2/ns/repo/blobs/uploads/<uuid><br/>Content-Range: bytes X-Y/*
        GO->>SM: State 2: Patch Upload
        SM->>DB: validate offset, get session
        SM->>S3: append chunk bytes
        S3-->>SM: bytes written
        SM->>DB: update offset
        SM-->>GO: updated Range + Location
        GO-->>C: 202 Range: 0-Y
    end

    Note over SM: State 3: Resume (if interrupted)
    C->>GO: GET /v2/ns/repo/blobs/uploads/<uuid>
    GO->>SM: get session state
    SM->>DB: read current offset
    SM-->>GO: offset + location
    GO-->>C: 204 Range: 0-currentOffset

    C->>GO: PUT /v2/ns/repo/blobs/uploads/<uuid>?digest=sha256:abc
    GO->>SM: State 4: Finalize
    SM->>S3: commit blob
    SM->>DB: verify digest, create blob record
    SM->>DB: delete upload session
    SM-->>GO: blobDigest
    GO-->>C: 201 Location: /v2/ns/repo/blobs/sha256:abc

    Note over SM: State 5: Abort/Timeout Cleanup<br/>(background: orphan session reaper)

    C->>GO: PUT /v2/ns/repo/manifests/tag
    GO->>DB: validate manifest references, store
    GO->>DB: create/update tag
    GO-->>C: 201 Created
```

> **Cross-runtime risk**: Upload sessions store hasher state as pickle+base64 in Python. During M2-M3, upload ownership is pinned by UUID (no mid-upload owner switch). Post-M4: JSON/protobuf cross-runtime hasher format.

---

## 6. Queue and Worker Dependency Map

```mermaid
graph TB
    subgraph queues["9 Queues"]
        q1["chunk_cleanup<br/>(no namespace)"]
        q2["imagestoragereplication<br/>(no namespace)"]
        q3["proxycacheblob<br/>(namespaced)"]
        q4["dockerfilebuild<br/>(namespaced, ORDERED)"]
        q5["notification<br/>(namespaced)"]
        q6["secscanv4<br/>(no namespace)"]
        q7["exportactionlogs<br/>(namespaced)"]
        q8["repositorygc<br/>(namespaced)"]
        q9["namespacegc<br/>(no namespace)"]
    end

    subgraph producers["Producers (Route/Model Layer)"]
        pr1["storage/swift.py<br/>(Swift chunk ops)"]
        pr2["util/registry/replication.py<br/>(push/mirror triggers)"]
        pr3["registry_proxy_model.py<br/>(proxy-cache pulls)"]
        pr4["endpoints/building.py<br/>(build API)"]
        pr5["notifications/__init__.py<br/>(event triggers)"]
        pr6["endpoints/secscan.py<br/>(Clair callbacks)"]
        pr7["data/logs_model/shared.py<br/>(log export API)"]
        pr8["data/model/repository.py<br/>(repo delete)"]
        pr9["data/model/user.py<br/>(namespace delete)"]
    end

    subgraph consumers["Consumers (Worker Phases)"]
        subgraph P2["P2: Queue Workers"]
            w1["chunkcleanupworker"]
            w2["storagereplication"]
            w3["proxycacheblobworker"]
            w4["notificationworker"]
            w5["securityscanningnotificationworker"]
            w6["exportactionlogsworker"]
        end

        subgraph P4["P4: GC Workers"]
            w7["repositorygcworker"]
            w8["namespacegcworker"]
        end

        subgraph P5["P5: Build Manager"]
            w9["builder<br/>(ordered queue,<br/>custom retry)"]
        end
    end

    pr1 --> q1 --> w1
    pr2 --> q2 --> w2
    pr3 --> q3 --> w3
    pr4 --> q4 --> w9
    pr5 --> q5 --> w4
    pr6 --> q6 --> w5
    pr7 --> q7 --> w6
    pr8 --> q8 --> w7
    pr9 --> q9 --> w8

    subgraph qmt_gates["Queue Mixed-Mode Tests (QMT)"]
        qmt1["QMT-CHUNK-CLEANUP<br/>gates: registry blob upload cutover"]
        qmt2["QMT-IMAGE-REPLICATION<br/>gates: replication route cutover"]
        qmt3["QMT-PROXY-CACHE-BLOB<br/>gates: proxy-cache route cutover"]
        qmt4["QMT-NOTIFICATION<br/>gates: api-v1 notification routes"]
        qmt5["QMT-EXPORT-ACTION-LOGS<br/>gates: api-v1 log export routes"]
        qmt6["QBT-DOCKERFILE-BUILD-ORDERED<br/>gates: build API + P5 builder"]
    end

    q1 -.-> qmt1
    q2 -.-> qmt2
    q3 -.-> qmt3
    q5 -.-> qmt4
    q7 -.-> qmt5
    q4 -.-> qmt6

    style queues fill:#fff3e0,stroke:#e65100
    style producers fill:#e8eaf6,stroke:#283593
    style consumers fill:#e3f2fd,stroke:#1565c0
    style qmt_gates fill:#fce4ec,stroke:#c62828
    style P2 fill:#e3f2fd,stroke:#1565c0
    style P4 fill:#e3f2fd,stroke:#1565c0
    style P5 fill:#e3f2fd,stroke:#1565c0
```

### Worker Rollout Phase Summary

```mermaid
gantt
    title Worker Migration Phases
    dateFormat X
    axisFormat %s

    section P0 Service Support
    dnsmasq, nginx, memcache, gunicorn-*, pushgateway (7)    :p0, 0, 1

    section P1 Schedulers
    buildlogsarchiver, globalpromstats, servicekey, etc (11)  :p1, 1, 2

    section P2 Queue Workers
    chunkcleanup, storagerepl, notification, etc (7)          :p2, 2, 3

    section P3 Complex Workers
    repomirror, securityworker, teamsync, etc (6)             :p3, 3, 4

    section P4 GC Workers
    gcworker, namespacegc, repositorygc (3)                   :p4, 4, 5

    section P5 Build Manager
    builder - ordered queue semantics (1)                      :p5, 5, 6
```

> **Queue contract**: At-least-once delivery, compare-and-swap claim via `id + state_id`. Build queue requires ordered claims. 3 queues (`proxy_cache_blob`, `secscan_notification`, `export_action_logs`) are missing from `all_queues` in `app.py` - namespace-deletion cleanup does not purge them.

---

## 7. Package Layout

Reconciled Go package structure from rewrite plan and OMR proposal.

```mermaid
graph TD
    subgraph cmd["cmd/ (entrypoints)"]
        quay_main["cmd/quay/main.go<br/>(single binary entrypoint)"]
    end

    subgraph cli["internal/cli/ (Cobra commands)"]
        serve["serve.go<br/>quay serve [--mode=mirror|standalone|full]"]
        install["install.go<br/>quay install [--profile=mirror|standalone|ha]"]
        upgrade["upgrade.go<br/>quay upgrade"]
        config_cmd["config.go<br/>quay config [validate|generate|print]"]
        migrate["migrate.go<br/>quay migrate (from mirror-registry)"]
        worker_cmd["worker.go<br/>quay worker <name>"]
        admin["admin.go<br/>quay admin [migrate|...]"]
    end

    subgraph core["internal/ (core packages)"]
        subgraph registry["registry/"]
            httpserver["httpserver/<br/>server.go, routes.go"]
            v2["v2/<br/>manifests, blobs,<br/>tags, catalog, auth"]
            v1["v1/<br/>images, tags,<br/>search, users"]
            uploads["uploads/<br/>sessions.go,<br/>state_machine.go"]
            schema1["schema1/<br/>signer, verifier,<br/>payload"]
            reg_auth["auth/<br/>middleware, scope,<br/>token_issuer"]
            reg_storage["storage/<br/>driver adapter"]
        end

        subgraph dal["dal/ (Data Access Layer)"]
            dbcore["dbcore/<br/>pool, retry, tx, metrics"]
            readreplica["readreplica/<br/>selector, policy"]
            crypto["crypto/<br/>field encrypt/decrypt"]
            repositories["repositories/<br/>postgres/sqlc generated"]
            testkit["testkit/<br/>fixtures, oracle helpers"]
        end

        subgraph switch_pkg["switch/"]
            owner["owner.go<br/>resolution algorithm"]
            switch_transport["transport.go<br/>config-provider polling"]
            canary_pkg["canary.go<br/>org/repo/user/percent"]
        end

        subgraph server["server/ (from OMR)"]
            http_srv["http.go<br/>merged from quay-distribution"]
        end

        subgraph config_pkg["config/"]
            loader["loader.go<br/>YAML loading + mode presets"]
            fieldgroups["fieldgroups/<br/>absorbed from config-tool"]
            validators["validators/<br/>field group validators"]
            generate["generate.go<br/>config generation"]
        end

        subgraph infra["infrastructure/"]
            auth_pkg["auth/<br/>JWT, OAuth, LDAP, OIDC"]
            storage_pkg["storage/<br/>S3, Azure, Swift, GCS,<br/>Rados, CloudFront, local"]
            cache_pkg["cache/<br/>Redis, in-memory"]
            tls_pkg["tls/<br/>cert generation"]
            quadlet_pkg["quadlet/<br/>systemd file generation"]
            nginx_pkg["nginx/<br/>config templating"]
            metrics_pkg["metrics/<br/>Prometheus + OTel"]
        end
    end

    quay_main --> cli
    cli --> core

    registry --> dal
    registry --> switch_pkg
    registry --> auth_pkg
    registry --> storage_pkg

    style cmd fill:#e8f5e9,stroke:#2e7d32
    style cli fill:#fff3e0,stroke:#e65100
    style registry fill:#e3f2fd,stroke:#1565c0
    style dal fill:#f3e5f5,stroke:#6a1b9a
    style switch_pkg fill:#fce4ec,stroke:#c62828
    style config_pkg fill:#fff9c4,stroke:#f57f17
    style infra fill:#e0f7fa,stroke:#00695c
    style server fill:#e8eaf6,stroke:#283593
```

### Package Dependency Flow

```mermaid
graph LR
    cmd["cmd/quay"] --> cli["internal/cli"]
    cli --> server["internal/server"]
    cli --> config["internal/config"]
    cli --> quadlet["internal/quadlet"]

    server --> registry["internal/registry"]
    server --> api["internal/api"]
    server --> switch["internal/switch"]

    registry --> dal["internal/dal"]
    registry --> auth["internal/auth"]
    registry --> storage["internal/storage"]

    api --> dal
    api --> auth

    dal --> dbcore["dal/dbcore<br/>(pgx/v5)"]
    dal --> crypto_pkg["dal/crypto"]

    switch --> config

    style cmd fill:#e8f5e9
    style dal fill:#f3e5f5
    style switch fill:#fce4ec
    style registry fill:#e3f2fd
```

> **Key integration point**: `internal/config/` absorbs both the config-tool field group validators and the OMR proposal's config generation. `internal/server/` merges the quay-distribution-main HTTP server. `internal/quadlet/` generates systemd unit files for containerized deployment, replacing the mirror-registry Ansible/EE orchestration.

---

## Appendix: Route Family Migration Sequence

Reference table for team review.

| Phase | Route Family | Method Rows | Mutating | Priority Notes |
|-------|-------------|-------------|----------|----------------|
| R1 | `registry-v2` | 19 | 9 | Start with auth/read, then push/upload/delete |
| R2 | `registry-v1` | 26 | 12 | Full compat required; do not de-scope |
| R3 | `oauth2` | 10 | 4 | Preserve callback + redirect semantics |
| R4 | `oauth1` | 1 | 0 | Preserve callback registration |
| R5 | `api-v1` | 268 | 153 | Largest surface; reads first, then mutations |
| R6 | `webhooks` | 3 | 3 | Protect signature/secret validation |
| R7 | `keys` | 4 | 2 | Keyserver endpoints |
| R8 | `secscan` | 3 | 1 | Coordinate with secscan notification queue |
| R9 | `realtime` | 2 | 0 | SSE/WebSocket endpoints |
| R10 | `well-known` | 2 | 0 | OIDC discovery |
| R11 | `web` | 65 | 4 | Triage contract-critical vs UI render |
| R12 | `other` | 10 | 3 | userfiles, _storage_proxy_auth |
| **Total** | | **413** | **191** | |
