#!/bin/bash
# init-garage.sh — Initialize Garage S3 for geo-replication testing.
# Creates two buckets (simulating two storage regions) and a fixed access key.
# Adapted from quay-operator hack/setup-kind-e2e.sh for docker-compose.
set -euo pipefail

CONTAINER="${GARAGE_CONTAINER:-quay-garage}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-$(command -v docker 2>/dev/null || command -v podman 2>/dev/null)}"
if [[ -z "${CONTAINER_RUNTIME}" ]]; then
  echo "ERROR: docker or podman is required" >&2
  exit 1
fi
ACCESS_KEY_ID="GKe2e0123456789abcdef01234"
SECRET_KEY="e2e0123456789abcdef0123456789abcdef0123456789abcdef01234567890ab"
BUCKETS=("quay-us-east" "quay-eu-west")

garage_exec() {
  "${CONTAINER_RUNTIME}" exec "${CONTAINER}" /garage "$@" 2>&1
}

echo "=== Initializing Garage S3 ==="

# Wait for Garage to be ready
for i in $(seq 1 30); do
  if garage_exec status >/dev/null 2>&1; then
    break
  fi
  [ "$i" -eq 30 ] && { echo "ERROR: Garage not ready after 30 attempts"; exit 1; }
  sleep 2
done

# Get node ID and assign layout
NODE_ID=$(garage_exec node id -q | tr -d '[:space:]')
echo "Node ID: ${NODE_ID}"
garage_exec layout assign -z dc1 -c 1G "${NODE_ID}" || true

# Apply layout (idempotent version loop — same pattern as operator)
applied=false
for v in 1 2 3 4 5; do
  if garage_exec layout apply --version "$v" 2>/dev/null; then
    echo "Layout applied (version $v)"
    applied=true
    break
  fi
done
if [[ "${applied}" != "true" ]]; then
  echo "ERROR: failed to apply Garage layout" >&2
  exit 1
fi

# Create buckets
for bucket in "${BUCKETS[@]}"; do
  garage_exec bucket create "${bucket}" || true
  echo "Bucket: ${bucket}"
done

# Import fixed access key (deterministic — no parsing needed)
garage_exec key import --yes "${ACCESS_KEY_ID}" "${SECRET_KEY}" -n quay-e2e 2>/dev/null || true

# Grant permissions on all buckets
for bucket in "${BUCKETS[@]}"; do
  garage_exec bucket allow --read --write --owner "${bucket}" --key "${ACCESS_KEY_ID}"
done

echo "=== Garage S3 ready ==="
echo "Endpoint: http://${CONTAINER}:3900"
echo "Access Key: ${ACCESS_KEY_ID}"
echo "Buckets: ${BUCKETS[*]}"
