# Registryd Design (`/v2` + `/v1`)

Status: Draft (blocking)
Last updated: 2026-02-09

## 1. Purpose

Define the implementation architecture for `registryd`, including `/v2` parity, `/v1` compatibility commitment, Schema1 signing, and upload state-machine behavior.

Primary source anchors:
- `registry.py`
- `endpoints/v1/`
- `endpoints/v2/`
- `image/docker/schema1.py`

## 2. Non-negotiable scope

1. `/v2/*` full parity.
2. `/v1/*` full support retained during migration and initial Go steady-state.
3. Existing auth contracts preserved (`X-Docker-Token`, JWT scope behavior, signed grants where applicable).
4. Chunked upload resume/finalize semantics remain wire-compatible.

## 3. Dependencies and version policy

Implementation baseline:
- Go: `1.23.x`
- Distribution integration: `github.com/distribution/distribution/v3` (pinned minor)
- Routing: `github.com/go-chi/chi/v5`
- Auth/JWT: `github.com/golang-jwt/jwt/v5`
- OpenTelemetry/Prometheus for request + upload metrics

Version policy:
- Pin explicit minor versions.
- Upgrade distribution dependency only after replaying `/v1` and `/v2` contract fixtures.

## 4. Package layout and file responsibilities

- `internal/registry/httpserver/`
  - `server.go` (listener, middleware chain, graceful shutdown)
  - `routes.go` (top-level route wiring)
- `internal/registry/v2/`
  - `manifests.go`, `blobs.go`, `tags.go`, `catalog.go`, `auth.go`
- `internal/registry/v1/`
  - `images.go`, `tags.go`, `search.go`, `users.go`
- `internal/registry/uploads/`
  - `sessions.go` (upload session persistence and resume)
  - `state_machine.go` (PATCH/PUT/DELETE flow)
- `internal/registry/auth/`
  - `middleware.go`, `scope.go`, `token_issuer.go`
- `internal/registry/schema1/`
  - `signer.go`, `verifier.go`, `payload.go`
- `internal/registry/storage/`
  - adapter interface to Go storage driver layer

## 5. Core interfaces (implementation stubs)

```go
package uploads

import (
    "context"
    "io"
)

type Session interface {
    ID() string
    Repository() string
    Offset() int64
    StartedAtUnix() int64
}

type Store interface {
    Start(ctx context.Context, repository string) (Session, error)
    Get(ctx context.Context, repository, uploadID string) (Session, error)
    Append(ctx context.Context, repository, uploadID string, body io.Reader, start int64) (nextOffset int64, err error)
    Commit(ctx context.Context, repository, uploadID, digest string) (blobDigest string, err error)
    Cancel(ctx context.Context, repository, uploadID string) error
}
```

```go
package schema1

type Signer interface {
    Sign(payload []byte, keyID string) ([]byte, error)
}

type Verifier interface {
    Verify(payload []byte) error
}
```

```go
package auth

import "net/http"

type ScopeResolver interface {
    Resolve(req *http.Request) ([]string, error)
}
```

## 6. Distribution component reuse boundaries

Use upstream components for:
- Manifest media-type handling where behavior matches Quay expectations.
- Blob streaming/chunk logic where resumability contract is preserved.

Keep Quay-owned adapters for:
- Token scope evaluation and issuer claims.
- Schema1 signing/verification semantics.
- Permission checks and quota/visibility policies.
- Cross-runtime upload session continuation.

## 7. `/v1` compatibility decision

Decision baseline in this plan:
- `/v1` remains supported in Go (`not deprecated in migration scope`).
- Any future deprecation requires a separate approved decision with customer impact analysis.

## 8. Upload state machine contract

Required states and behavior:
1. Start upload: create session and return location.
2. Patch upload: append bytes with range validation.
3. Resume upload: recover state after restart/failover.
4. Finalize upload: digest verification and commit.
5. Abort/timeout cleanup: preserve orphan cleanup semantics.

Mixed-runtime rule:
- Python and Go instances must be able to continue each other's upload sessions while capability ownership is shared.

Failure rules:
- Range mismatch returns same status code family as current Python handlers.
- Commit digest mismatch does not leave partial committed state.
- Canceled session cannot be resumed.

## 9. Upload hasher state serialization (dual-runtime blocker)

Current Python behavior:
- `BlobUpload.sha_state` and `BlobUpload.piece_sha_state` are persisted using Python pickle + base64 (`data/fields.py`, `data/database.py`).
- This format is not natively consumable from Go.

Risk:
- Mixed-runtime chunk uploads can fail if runtime ownership changes mid-upload and the receiving runtime cannot read hasher state written by the other runtime.

M2-M3 strategy (required):
1. Pin upload ownership by upload UUID for active sessions (`python` OR `go`, never mixed within one upload session).
2. Reject cross-runtime session continuation with explicit, retryable error signaling while pinning is active.
3. Keep rollback behavior explicit: owner switch for new uploads must not migrate in-flight sessions.

M4+ strategy (required migration path):
1. Introduce a non-pickle cross-runtime hasher state format (JSON/protobuf) with version field.
2. Python reads old+new formats during migration window.
3. Go reads old+new formats only if a validated decoder is implemented; otherwise continue ownership pinning.
4. Remove pickle-only writes only after cross-runtime continuation tests are green.

Required tests:
- Start upload in Python, continue/finalize in Python (baseline).
- Start upload in Go, continue/finalize in Go (baseline).
- Start upload in Python, continue in Go:
  - expected controlled failure during pinning phase
  - expected success only after shared format rollout
- Start upload in Go, continue in Python with same expectations.

## 10. Schema1 migration requirements

- Preserve RS256 signing and verification behavior for legacy schema1 manifests.
- Keep deterministic serialization/signing behavior compatible with existing clients.
- Cross-runtime fixture tests:
  - Python-signed payload verifies in Go.
  - Go-signed payload verifies in Python (during mixed mode).

Fixture contract:
- `tests/rewrite/contracts/registry/schema1/fixtures/<name>.json`
  - `manifest_payload`
  - `headers`
  - `expected_signature_key_id`
  - `expected_verification_result`

## 11. Observability and control-plane integration

- Emit per-route-family parity metrics (`v1`, `v2`).
- Emit upload state transition counters and error-code histograms.
- Emit auth-scope rejection counters by reason.
- Integrate with owner switches from `switch_spec.md`.

Required labels:
- `route_family`
- `capability_owner` (`python|go`)
- `status_class`
- `error_reason` (bounded cardinality)

## 12. Concrete implementation example

Reference operation: `PATCH /v2/<repo>/blobs/uploads/<uuid>`.

Implementation requirements:
1. Resolve upload session from shared store.
2. Validate `Content-Range` with current offset.
3. Append bytes with monotonic offset guarantee.
4. Return updated `Range` header and upload `Location`.
5. Preserve retry behavior on transient storage errors.

## 13. Exit criteria (gate G11)

- Architecture approved by registry + security owners.
- `internal/registry/...` package scaffold compiles with pinned dependencies.
- Schema1 compatibility tests green.
- Chunked upload cross-runtime continuation validated.
- Upload hasher state strategy is implemented and tested for current migration phase (pinning or shared format).
- `/v1` and `/v2` rollback drills proven under canary traffic.
