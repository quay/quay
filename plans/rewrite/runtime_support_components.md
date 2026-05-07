# Runtime Support Components Inventory

Status: Draft
Last updated: 2026-02-08

## 1. Purpose

Track non-endpoint, non-supervisor runtime components initialized in-process that still carry user-visible behavior or operational side effects.

## 2. Initialization anchor

Primary anchor: `app.py` extension initialization block.

## 3. Components in migration scope

| Component | Source | Runtime behavior to preserve | Risk class |
|---|---|---|---|
| `PrometheusPlugin` | `util/metrics/prometheus.py` | Background push thread (`ThreadPusher`) and request metrics shaping | High |
| `Analytics` | `util/saas/analytics.py` | Optional Mixpanel queue + sender thread behavior | Medium |
| `UserEventsBuilderModule` | `data/userevent.py` | Realtime pub/sub semantics, event stream heartbeat behavior | High |
| `PullMetricsBuilderModule` | `util/pullmetrics.py` | Async pull tracking + Redis script semantics + thread pool behavior | High |
| `BuildCanceller` | `buildman/manager/buildcanceller.py` | Build cancel orchestration behavior from API paths | High |
| `Userfiles` | `data/userfiles.py` | App-level route registration + file serving/upload semantics | High |
| `DownloadProxy` | `storage/downloadproxy.py` | Storage proxy JWT validation endpoint semantics (`/_storage_proxy_auth`) | High |
| `MarketplaceUserApi` / `MarketplaceSubscriptionApi` | `util/marketplace.py` | External entitlement lookup/reconciliation API integration | Medium |

## 4. Migration policy

- These components must be explicitly mapped to Go ownership or intentional retirement.
- Threaded/background side effects must have observability parity and failure-mode parity.
- Any component that registers HTTP routes must be represented in route tracker artifacts.

## 5. Required outputs

- `plans/rewrite/generated/runtime_component_mapping.csv`: python component -> go owner package -> parity tests.
- `plans/rewrite/generated/runtime_component_mapping_summary.md`
- `plans/rewrite/runtime_component_execution_plan.md`
- Runtime-side-effect test cases for thread/pool based components.
