# `internal/e2e/` agent guidance

This directory owns in-process end-to-end tests for composed Go products. Follow the repository-level `AGENTS.md` in addition to these rules.

## Scope and placement

- Put scenarios under `internal/e2e/<product>/`; mirror-registry work belongs in `internal/e2e/mirrorregistry/`.
- Use an external test package such as `mirrorregistry_test` for black-box scenarios.
- Keep product-owned fixtures and clients under `<product>/internal/e2etest/`. The nested `internal` boundary is deliberate: do not import these helpers from production code or sibling product suites.
- Do not move helpers upward preemptively. Share only when at least two product suites need the same stable abstraction.

## Test design

- Start the real product composition and serve its top-level `App.Handler()` on an ephemeral loopback listener.
- Test through public HTTP behavior. Do not add direct Distribution adapters, an `oci.Registry` abstraction, or a second routing/composition path just for E2E tests.
- Give each test its own application, database, storage, signing material, listener, and metrics registry. Do not introduce a shared global harness.
- Reserve the listener before composition when its address affects public URLs, token realms, or audiences.
- Use `t.Context()`, finite client timeouts, and `t.Cleanup()`. Close the HTTP server before the application and temporary resources.
- Consume and close every response body. Avoid sleeps, fixed ports, external processes, and readiness polling when startup is synchronous.
- Keep fixtures deterministic and clients narrow. Add options, retries, caching, or dependencies only for a demonstrated test case.
- Assert externally observable outcomes, not only accepted status codes.

## Verification

For mirror-registry E2E changes, run at minimum:

```bash
go test ./internal/e2e/mirrorregistry/...
go test -race ./internal/e2e/mirrorregistry/...
golangci-lint run --timeout=5m ./internal/e2e/mirrorregistry/...
go vet ./internal/e2e/mirrorregistry/...
```

Broaden to `go test ./...`, `go vet ./...`, and the full Go lint command when changing shared helpers or composition contracts.
