# Mirror Health and Metrics — Manual QA (Podman / local dev)

Manual validation guide for repository and organization mirror **health endpoints** and **Prometheus metrics** using the local Podman/Docker Compose stack.

For metric names, response schemas, and alert examples, see [mirroring-metrics.md](mirroring-metrics.md).

## Prerequisites

1. **Features enabled** in `local-dev/stack/config.yaml`:

   ```yaml
   FEATURE_REPO_MIRROR: true
   FEATURE_ORG_MIRROR: true
   ```

2. **Mirror worker running** — metrics are emitted from the `repomirror` container, not the main `quay` app:

   ```bash
   make local-dev-up-with-repomirror
   ```

   This starts `quay-quay` (API/UI on port 8080) and `quay-repomirror` (mirror worker). The worker shares the Quay container network and pushes metrics to PushGateway on port **9091**.

3. **Authenticated session** — health endpoints require a fresh login (`@require_fresh_login`). Use cookie-based sign-in for `curl` tests below.

## Authentication helper

```bash
export QUAY_URL="${QUAY_URL:-http://localhost:8080}"
export COOKIES="/tmp/quay-mirror-health-cookies.txt"

curl -s -c "$COOKIES" -X POST "$QUAY_URL/api/v1/signin" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq .
```

Use `-b "$COOKIES"` on subsequent requests. Replace credentials with your local superuser.

---

## Repository mirror health

### API

```bash
# Global health (superuser or global readonly superuser)
curl -s -b "$COOKIES" -w "\nHTTP %{http_code}\n" \
  "$QUAY_URL/api/v1/repository/mirror/health" | jq

# Namespace-scoped
curl -s -b "$COOKIES" \
  "$QUAY_URL/api/v1/repository/mirror/health?namespace=devtable" | jq

# Per-repository breakdown
curl -s -b "$COOKIES" \
  "$QUAY_URL/api/v1/repository/mirror/health?detailed=true&limit=50" | jq
```

**Expected HTTP status:** `200` when `"healthy": true`, `503` when `"healthy": false`.

**Cache-Control:** `no-cache, no-store, must-revalidate`

### Metrics (mirror worker pod)

Repository mirror per-repo metrics use the `quay_repository_mirror_*` prefix:

```bash
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep -E '^quay_repository_mirror_(pending_tags|last_sync_status|sync_complete|sync_failures_total|last_sync_timestamp|workers_active)'
```

On typical local dev, `quay-quay` (API) reports `workers.active: 0` and `tags_pending: 0` because the mirror worker runs in a separate process. That is expected — scrape **`quay-repomirror`** for worker metrics.

---

## Organization mirror health

### Setup (minimal)

1. Create or use an organization (e.g. `coreos`) with a mirror robot.
2. Configure org mirroring via the API:

   ```bash
   curl -s -b "$COOKIES" -X POST "$QUAY_URL/api/v1/organization/coreos/mirror" \
     -H "Content-Type: application/json" \
     -d '{
       "external_registry_type": "quay",
       "external_registry_url": "https://quay.io",
       "external_namespace": "coreos",
       "robot_username": "coreos+mirrorbot",
       "visibility": "public",
       "sync_interval": 3600,
       "sync_start_date": "2026-01-01T00:00:00Z"
     }' | jq .
   ```

3. Trigger discovery/sync (optional):

   ```bash
   curl -s -b "$COOKIES" -X POST \
     "$QUAY_URL/api/v1/organization/coreos/mirror/sync-now" | jq .
   ```

4. Wait for the mirror worker to run discovery and tag sync cycles (`ORG_MIRROR_INTERVAL`, default 30s in worker).

### Health API

```bash
# Summary (org member, org admin, or superuser)
curl -s -b "$COOKIES" -w "\nHTTP %{http_code}\n" \
  "$QUAY_URL/api/v1/organization/coreos/mirror/health" | jq

# Per-discovered-repository breakdown
curl -s -b "$COOKIES" \
  "$QUAY_URL/api/v1/organization/coreos/mirror/health?detailed=true&limit=50&offset=0" | jq
```

**RBAC checks:**

| Caller | Expected |
|--------|----------|
| Org member | `200` or `503` |
| Superuser | `200` or `503` |
| User not in org | `401` |
| Unauthenticated | `401` |
| Org without mirror config | `404` |
| Unknown organization | `404` |

**Response shape (summary):**

```json
{
  "healthy": true,
  "workers": { "active": 0, "configured": 0, "status": "healthy" },
  "organization": {
    "syncing": 0,
    "completed": 1,
    "failed": 0,
    "never_run": 0,
    "last_discovery_status": 1,
    "last_discovery_timestamp": "2026-06-18T10:34:59.935806Z",
    "repositories": {
      "total": 12,
      "syncing": 0,
      "completed": 11,
      "failed": 1,
      "never_run": 0,
      "skipped": 0,
      "tags_pending": 0
    }
  },
  "last_check": "2026-06-18T11:10:24.403211Z",
  "issues": []
}
```

`organization.repositories.tags_pending` and `workers.active` are often **0** on the API pod; they reflect the in-process Prometheus registry. For live values, use metrics on the mirror worker (below).

### Metrics (mirror worker pod)

Org mirror per-repo and discovery metrics use the `quay_org_mirror_*` prefix:

```bash
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep -E '^quay_org_mirror_'
```

Useful series to verify after a sync cycle:

```bash
# Per-repository sync status (canonical series)
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep 'quay_org_mirror_last_sync_status{.*last_error_reason=""}'

# Discovery status for the org namespace
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep 'quay_org_mirror_last_discovery_status'

# Pending tags during an in-progress sync
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep quay_org_mirror_pending_tags
```

Existing aggregate metrics (unchanged):

```bash
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep -E 'quay_org_mirror_(repo_sync_total|discovery_total|repos_discovered)'
```

Worker liveness is shared with repo mirroring:

```bash
podman exec quay-repomirror \
  curl -s http://localhost:9091/metrics \
  | grep quay_repository_mirror_workers_active
```

---

## OpenShift validation

On OpenShift, mirror metrics are on **mirror worker pods**, not `quay-app` pods.

1. Find mirror worker pods:

   ```bash
   oc get pods -n <namespace> -l <mirror-worker-label>
   ```

2. Exec into a mirror pod and scrape PushGateway:

   ```bash
   oc exec -it <mirror-pod> -n <namespace> -- \
     curl -s http://localhost:9091/metrics | grep quay_org_mirror
   ```

3. Confirm `quay_repository_mirror_workers_active` is `1` on each running mirror pod; sum across targets for cluster total.

4. Health API — call from outside the cluster (or via port-forward to Quay):

   ```bash
   curl -s -b "$COOKIES" \
     "https://<quay-route>/api/v1/organization/<org>/mirror/health" | jq
   ```

5. **ServiceMonitor / scrape config** — wiring mirror pods into Prometheus is deployment-specific and out of scope for this doc. Ensure your scrape config targets mirror worker pods on port `9091`, not only `quay-app`.

---

## Troubleshooting

| Symptom | Likely cause | What to check |
|---------|----------------|---------------|
| Health API `tags_pending: 0` always | API pod has no worker metrics | Scrape `quay-repomirror` / mirror worker pods |
| Health API `workers.active: 0` | Same as above | `quay_repository_mirror_workers_active` on worker pod |
| No `quay_org_mirror_*` metrics | Org mirror not configured or worker not running | `FEATURE_ORG_MIRROR`, `make local-dev-up-with-repomirror` |
| `403` on health API | Stale session | Re-run sign-in (`require_fresh_login`) |
| `404` on org health | No `OrgMirrorConfig` for org | `GET /api/v1/organization/<org>/mirror` |

---

## Related documentation

- [mirroring-metrics.md](mirroring-metrics.md) — metric catalog, health schemas, PromQL examples
- [prometheus.md](prometheus.md) — PushGateway and cardinality notes
- [Repository mirroring guide](https://docs.projectquay.io/repo_mirror.html)
