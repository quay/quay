# Go Module and CI Bootstrap Strategy

Status: Draft (blocking)
Last updated: 2026-02-09

## 1. Purpose

Define how Go code is introduced into this repo with reproducible builds, linting, and CI gates before feature implementation starts.

## 2. Module strategy

Recommended baseline:
- Single root module: `github.com/quay/quay`
- Go version: `1.23.x`
- Use `internal/` for rewrite implementation packages during mixed-runtime migration.

Why single module:
- Simplifies shared dependency/version management.
- Keeps route/worker/storage/auth implementations under one CI surface.
- Avoids multi-module drift while APIs are still moving.

## 3. Initial directory scaffold

Minimum compile target:
- `internal/dal/`
- `internal/registry/`
- `internal/switch/`
- `internal/auth/`
- `internal/storage/`
- `internal/crypto/`
- `cmd/registryd/`
- `cmd/api-service/`
- `cmd/workerd/`

Each package should include at least one `_test.go` file so CI validates test harness wiring from day one.

## 4. CI pipeline requirements

Required checks on every PR touching Go code:
1. `go mod tidy` cleanliness check (no diff).
2. `go test ./...`
3. `go vet ./...`
4. `golangci-lint run` (with pinned config/version)

Recommended staged checks:
- Fast tier (required): `go test` on unit packages, `go vet`.
- Slow tier (required before merge): contract suites under `tests/rewrite/contracts/`.

## 5. Cross-language contract wiring

Go test harness must support:
- Reading fixture artifacts generated from Python-oracle runs.
- Producing normalized result JSON for diffing.
- Annotating tracker rows with `test_file`, `last_run_commit`, and `last_passed_at`.

## 6. Ownership and approval

- Primary owners: `runtime-platform` + `release-management`.
- Security review required for crypto/TLS dependencies.
- Any dependency with C bindings requires explicit FIPS compatibility signoff.

## 7. Exit criteria (M0 prerequisite)

- `go.mod` and `go.sum` exist at repo root.
- Minimum package scaffold compiles.
- CI runs `go test ./...` and `go vet ./...` successfully.
- At least one contract test package is runnable in CI.
