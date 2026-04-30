---
name: cluster-provision
description: >
  Provision an ephemeral OpenShift cluster via the OpenShift CI Gangway API.
  Claims a cluster from a Hive ClusterPool, downloads and decrypts kubeconfig,
  and validates connectivity. Requires GANGWAY_TOKEN and CLUSTER_PROVISION_KEY
  env vars. Clusters auto-expire after ~4 hours. Use when you need a real
  OpenShift cluster for blackbox testing or integration work.
argument-hint: "[KUBECONFIG_PATH] [OCP_VERSION]"
allowed-tools:
  - Bash(bash .claude/scripts/cluster-provision.sh *)
  - Bash(oc --kubeconfig=*)
  - Read
---

# Cluster Provision

Provision an ephemeral OpenShift cluster from a Hive ClusterPool via the OpenShift CI Gangway REST API.

## Arguments

Parse `$ARGUMENTS` into at most two values before invoking Bash:
- **Arg 1**: KUBECONFIG path (default: `/tmp/k`)
- **Arg 2**: OCP version (default: `4.18`)

Set variables from `$ARGUMENTS`:
```text
KUBECONFIG_PATH = first arg or /tmp/k
OCP_VERSION = second arg or 4.18
```

## Step 1: Provision the cluster

```bash
bash .claude/scripts/cluster-provision.sh up "$KUBECONFIG_PATH" "$OCP_VERSION"
```

The script handles everything: triggering the Gangway API, polling for readiness, downloading the kubeconfig, and validating connectivity. Wait for the `=== Cluster Ready ===` output.

## Step 2: Verify

```bash
oc --kubeconfig="$KUBECONFIG_PATH" whoami
oc --kubeconfig="$KUBECONFIG_PATH" get nodes
```

## Step 3: Report

Summarize connection status and remind user:
- The cluster is ready
- Kubeconfig path
- Cluster server URL
- Cluster auto-expires in ~4 hours
- Prow job URL for reference

## Status

```bash
bash .claude/scripts/cluster-provision.sh status
```

Shows execution ID, elapsed time, estimated remaining time, and tests cluster connectivity.

## Teardown

```bash
bash .claude/scripts/cluster-provision.sh down
```

Removes local state and kubeconfig. Clusters auto-expire after ~4 hours via Hive — no explicit API teardown needed.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `GANGWAY_TOKEN is not set` | Run: `oc login https://api.ci.l2s4.p1.openshiftapps.com:6443 --web && export GANGWAY_TOKEN=$(oc whoami -t)` |
| `HTTP 401` | Token expired — re-authenticate with `oc login` |
| `CLUSTER_PROVISION_KEY is not set` | Contact the Quay CI team for the decryption passphrase |
| `HTTP 404` on trigger | ProwJob `periodic-ci-quay-quay-master-claim-claim-cluster` not configured in `openshift/release` |
| Timeout after 40 min | Pool exhausted or job stuck — check the Prow job URL |
| Kubeconfig download fails | GCS artifact path mismatch — download manually from the Prow job artifacts tab |
| `oc whoami` fails | Cluster not fully ready or VPN required — wait and retry |
