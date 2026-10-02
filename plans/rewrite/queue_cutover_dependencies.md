# Queue Cutover Dependency Plan

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Make route and worker rollout ordering explicit where queue producers and consumers are split across endpoint, model, and worker code.

## 2. Primary evidence

- `plans/rewrite/generated/queue_inventory.md`
- `plans/rewrite/generated/queue_payload_inventory.md`
- `plans/rewrite/generated/queue_worker_contract_tests.csv`
- `plans/rewrite/generated/route_worker_dependency_matrix.md`

## 3. Dependency matrix (planning baseline)

| Queue | Producer surface (inferred) | Consumer process wave | Route/API dependency (inferred) | Required sequencing rule |
|---|---|---|---|---|
| `chunk_cleanup` | storage backend operations (`storage/swift.py`) | `P2` (`chunkcleanupworker`) | registry blob/layer upload paths (`/v1`, `/v2`) | Keep mixed-mode queue compatibility (`QMT-CHUNK-CLEANUP`) green before registry owner flips. |
| `imagestoragereplication` | replication model/service (`util/registry/replication.py`) | `P2` (`storagereplication`) | repo mirror/replication API + config-driven replication flows | Do not complete replication feature cutover until `QMT-IMAGE-REPLICATION` passes in mixed producer/consumer mode. |
| `proxycacheblob` | proxy model (`data/registry_model/registry_proxy_model.py`) | `P2` (`proxycacheblobworker`) | proxy-cache pulls on registry endpoints | Gate proxy-cache route ownership on `QMT-PROXY-CACHE-BLOB` + worker `P2` stability. |
| `dockerfilebuild` | build initiation (`endpoints/building.py`) | `P5` (`builder`) | build API/UI flows (`api-v1` + `web`) | Build route cutover cannot finalize until ordered-queue tests (`QBT-DOCKERFILE-BUILD-ORDERED`) and `P5` builder parity pass. |
| `notification` | notification API + model (`endpoints/api/repositorynotification_models_pre_oci.py`, `notifications/__init__.py`) | `P2` (`notificationworker`) | notification config endpoints and event-producing routes | Require `QMT-NOTIFICATION` prior to `api-v1` notification route owner flips. |
| `secscanv4` | secscan endpoint (`endpoints/secscan.py`) | `P2` (`securityscanningnotificationworker`) | secscan callback/status endpoints | Run `A3` secscan route wave and `P2` worker wave as a coupled rollout unit. |
| `exportactionlogs` | logs model (`data/logs_model/shared.py`) | `P2` (`exportactionlogsworker`) | log export API routes (`api-v1` logs/superuser) | Complete `QMT-EXPORT-ACTION-LOGS` before broad `api-v1` ownership expansion. |
| `repositorygc` | repository model delete paths (`data/model/repository.py`) | `P4` (`repositorygcworker`) | repo delete/admin lifecycle endpoints | Keep Python owner fallback until `P4` GC lock/retry parity is verified. |
| `namespacegc` | namespace/user model delete paths (`data/model/user.py`) | `P4` (`namespacegcworker`) | org/user lifecycle endpoints | Couple destructive namespace lifecycle cutover with `P4` GC parity and rollback drill. |

## 4. Execution policy

1. Treat queue compatibility tests (`QMT-*`) as preconditions for route-family owner changes that can enqueue the same payloads.
2. If producers are model/service driven (not directly in route files), require explicit call-path evidence in signoff notes before route-wave completion.
3. Promote worker waves `P2`, `P4`, `P5` to `verified` before final Go ownership for dependent route families.

## 5. Open validation items

- Confirm exact route IDs that trigger each model/service producer path for:
  - `chunk_cleanup`
  - `imagestoragereplication`
  - `proxycacheblob`
  - `exportactionlogs`
  - `repositorygc`
  - `namespacegc`
- Implement producer-path extraction support in signoff evidence:
  - static pass: AST call-path mapping from endpoint handlers to queue producers
  - dynamic pass: integration traces for queue enqueue events during route contract tests
- Record confirmed route IDs and evidence links in checklist `verification_notes` before promoting affected waves to `verified`.
