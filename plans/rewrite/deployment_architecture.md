# Deployment Architecture (Kubernetes + VM)

Status: Draft
Last updated: 2026-02-09

## 1. Purpose

Define how Go rewrite components run in both Kubernetes and standalone VM deployments.

## 2. Binary and process model

Recommended model: single Go binary with subcommands.

Examples:
- `quay serve api-service`
- `quay serve registryd`
- `quay worker notification`
- `quay worker builder`
- `quay admin migrate`

Benefits:
- Shared config and observability stack.
- Easier VM packaging and K8s workload specialization.

## 3. Kubernetes deployment shape

- Dedicated Deployments for `api-service` and `registryd`.
- Separate worker Deployments per worker family (queue-heavy workers isolated).
- Horizontal autoscaling based on queue lag and request latency.
- Config-provider distribution for switch ownership state.

## 4. Standalone VM deployment shape

- Systemd-managed processes for `api-service`, `registryd`, and required workers.
- Optional all-in-one compatibility profile for transitional installs.
- Explicit health probes and restart policies per process.

## 5. Networking and ports

- Preserve externally visible ports/protocol behavior per `tls_security_posture.md`.
- Keep compatibility for proxy protocol and internal grpc side channels where still required.

## 6. Operational requirements

- Unified readiness/liveness endpoints for all Go services.
- Structured logs and metrics with service labels.
- Rollback script/runbook for owner-switch fallback to Python services.

## 7. Exit criteria

- Reference deployment manifests/templates for both K8s and VM are documented.
- First canary environment runs entirely on this model.
- Process supervision equivalence with legacy `supervisord` is proven.
