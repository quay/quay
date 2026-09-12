# Capability Cutover Matrix (Python vs Go)

Status: Expanded
Last updated: 2026-02-08

## 1. Purpose

Track per-capability ownership and cutover controls.

Owner values:
- `python`
- `go`

Canary rollout is selector-based (org/repo/user/percent), not an owner value.

## 2. Current control reality

Existing Python controls today:
- Endpoint behavior flags (`show_if` / `route_show_if`) for optional features.
- Process-level autostart control via supervisor (`QUAY_SERVICES`, `QUAY_OVERRIDE_SERVICES`).
- Feature flags controlling worker startup.

Missing today (must be added for safe rewrite):
- Per-capability route owner switches for Python vs Go endpoint routing.
- Per-process worker owner switches (`python|go|off`).
- Runtime switch propagation with fast failback behavior.

## 3. Matrix

| Capability | Python source | Existing Python disable control | Required owner switch | Rollback control | Owner |
|---|---|---|---|---|---|
| `/v2` pull/push/blob/manifest/auth/referrers | `endpoints/v2/*` | none per capability (global runtime only) | `ROUTE_OWNER_FAMILY_REGISTRY_V2` + capability overrides | switch -> `python` | `python` |
| `/v1` full surface | `endpoints/v1/*` | none per capability (global runtime only) | `ROUTE_OWNER_FAMILY_REGISTRY_V1` + capability overrides | switch -> `python` | `python` |
| `/api/v1` resources | `endpoints/api/*` | limited feature flags only | `ROUTE_OWNER_FAMILY_API_V1` + capability overrides | switch -> `python` | `python` |
| `/oauth*` dynamic + static | `endpoints/oauth/*`, `endpoints/web.py` | limited feature flags only | `ROUTE_OWNER_FAMILY_OAUTH` + route overrides | switch -> `python` | `python` |
| `/webhooks/*` | `endpoints/webhooks.py` | none per endpoint | `ROUTE_OWNER_FAMILY_WEBHOOKS` | switch -> `python` | `python` |
| `/keys/*` | `endpoints/keyserver/*` | none per endpoint | `ROUTE_OWNER_FAMILY_KEYS` | switch -> `python` | `python` |
| `/secscan/*` | `endpoints/secscan.py` | `features.SECURITY_*` gates only | `ROUTE_OWNER_FAMILY_SECSCAN` | switch -> `python` | `python` |
| `/realtime/*` | `endpoints/realtime.py` | none per endpoint | `ROUTE_OWNER_FAMILY_REALTIME` | switch -> `python` | `python` |
| `/.well-known/*` | `endpoints/wellknown.py` | none per endpoint | `ROUTE_OWNER_FAMILY_WELLKNOWN` | switch -> `python` | `python` |
| App-level `add_url_rule` routes (`/userfiles/*`, `/_storage_proxy_auth`) | `data/userfiles.py`, `storage/downloadproxy.py` | none per endpoint | `ROUTE_OWNER_FAMILY_OTHER` + route overrides | switch -> `python` | `python` |
| Queue workers (all) | `workers/*` | `QUAY_OVERRIDE_SERVICES`, feature flags | `WORKER_OWNER_<PROGRAM>` (new enum) | switch -> `python` | `python` |
| Build manager | `buildman/*` | supervisor `builder` program enable/disable + `BUILD_SUPPORT` | `WORKER_OWNER_BUILDER` | switch -> `python` | `python` |

## 4. Minimum switch set to implement in Go-era control plane

- Route-owner switches for each route family and selected high-risk sub-capabilities.
- Worker-owner switches for each worker program.
- Shared canary selector controls (org/repo/tenant).
- Atomic rollback path that flips ownership back to Python in one change operation.
- Specification source: `plans/rewrite/switch_spec.md`.
- Transport/distribution source: `plans/rewrite/switch_transport_design.md`.

## 5. Sequencing policy

1. Add routing and worker ownership controls first.
2. Land Go capability behind disabled switches.
3. Run parity suite and canary with scoped selectors.
4. Move owner=`go` for scoped cohorts.
5. Disable Python capability only after stability window and rollback rehearsal.
