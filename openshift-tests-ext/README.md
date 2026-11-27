# Quay OpenShift Tests Extension (OTE)

This directory contains the OpenShift Tests Extension (OTE) binary for Quay registry testing.

## Overview

The `quay-tests` binary implements the OTE v1.1 protocol to enable Quay testing within the OpenShift test framework using the `openshift-tests` command with the `--extension-local-binaries` flag.

## Structure

```
openshift-tests-ext/
├── cmd/quay-tests/      # Binary entry point
├── pkg/adapter/         # Generic test execution adapter
├── test/quay/           # Test scenarios (JSON) and scripts
│   ├── scripts/         # Test scripts (embedded in binary)
│   ├── scenarios.json   # Test definitions
│   └── embed.go         # Embed directives
├── go.mod               # Go module definition
└── Makefile             # Build automation
```

## Building

```bash
make build
```

## Running Tests

### Standalone (for development)

```bash
# Run all Quay tests
INTEROP_SCRIPTS_DIR=./test/quay/scripts ./quay-tests run-suite quay/all

# Run smoke tests only
INTEROP_SCRIPTS_DIR=./test/quay/scripts ./quay-tests run-suite quay/smoke

# List available tests
./quay-tests list tests

# Show extension info
./quay-tests info
```

### With openshift-tests (production)

```bash
openshift-tests run-suite quay/all \
  --extension-local-binaries /usr/bin/quay-tests.gz \
  --junit-dir ./junit
```

## Test Suites

- `quay/all` - All Quay tests
- `quay/smoke` - Quay smoke tests (subset with SMOKE tag)

## Adding Tests

Tests are defined in `test/quay/scenarios.json`. To add a new test:

1. Create a test script in `test/quay/scripts/`
2. Add a scenario entry to `test/quay/scenarios.json`
3. Rebuild the binary with `make build`

## CI Integration

This binary is built as part of CI composite containers and invoked by step-registry refs in the openshift/release repository.

See: `ci-operator/step-registry/interop/quay/` in openshift/release

## Related

- OpenShift Tests Extension framework: https://github.com/openshift-eng/openshift-tests-extension
- OTE Protocol spec: https://github.com/openshift-eng/openshift-tests-extension/blob/main/docs/protocol.md
- Component Readiness: https://github.com/openshift/component-readiness
