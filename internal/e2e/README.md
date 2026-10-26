# Go end-to-end tests

This tree contains in-process, black-box tests for complete Go application compositions. These tests sit above package integration tests and below process-level installation and conformance jobs: they start a real application handler on a loopback listener and exercise it through its public HTTP boundary.

## Layout

Keep tests grouped by product:

```text
internal/e2e/
└── mirrorregistry/
    ├── registry_test.go
    └── internal/e2etest/
        ├── harness.go
        └── registry.go
```

A product directory owns its fixtures, clients, and scenarios. New mirror-registry scenarios belong under `mirrorregistry/`; a different composed product should get a sibling directory rather than sharing one large test suite.

The second `internal/` is intentional. Go restricts `mirrorregistry/internal/e2etest` imports to the owning mirror-registry E2E subtree. This keeps fixture APIs out of production packages and prevents sibling product suites from coupling to product-specific setup. Promote a helper only after multiple product suites have a concrete, stable need for the same behavior.

## Building out a suite

- Construct the production composition (`mirrorregistry.New`) and serve its `App.Handler()`; do not build a parallel application stack for tests.
- Exercise user-visible behavior over HTTP when routing, authentication, headers, redirects, or upload locations matter.
- Give each test an isolated database, storage directory, signing material, listener, and metrics state.
- Use ephemeral loopback ports, bounded clients, `t.Context()`, and `t.Cleanup()`.
- Drain HTTP work before closing the application and removing its temporary files.
- Keep clients and fixtures small. Add operations and options only for scenarios that exist.
- Leave process lifecycle, TLS installation, container behavior, and broad OCI conformance to their dedicated jobs.

Run the product suite with:

```bash
go test ./internal/e2e/mirrorregistry/...
go test -race ./internal/e2e/mirrorregistry/...
```
