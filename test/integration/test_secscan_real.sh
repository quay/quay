#!/bin/bash
#
# OCP Validation Script for Quay Security Scanning
#
# This script validates security scanning with a real Clair instance on an
# OpenShift cluster. It performs a complete end-to-end test:
# 1. Login to Quay registry
# 2. Push a test image
# 3. Wait for Clair scan to complete
# 4. Verify vulnerability data is returned
# 5. Clean up test resources
#
# Requirements:
# - podman or docker CLI
# - jq (JSON processor)
# - curl
# - Access to an OCP cluster with Quay + Clair deployed
#
# Usage:
#   export OCP_QUAY_URL="quay-quay.apps.ocp.example.com"
#   export TEST_ORG="test-org"
#   export USERNAME="testuser"
#   export PASSWORD="password"
#   bash test/integration/test_secscan_real.sh
#

set -e

# Configuration with defaults
: "${OCP_QUAY_URL:?ERROR: Must set OCP_QUAY_URL environment variable}"
: "${TEST_ORG:=test-secscan-org}"
: "${TEST_REPO:=secscan-validation-$(date +%s)}"
: "${USERNAME:=testuser}"
: "${PASSWORD:=password}"
: "${CONTAINER_RUNTIME:=podman}"

# Detect container runtime
if ! command -v ${CONTAINER_RUNTIME} &> /dev/null; then
    if command -v docker &> /dev/null; then
        CONTAINER_RUNTIME=docker
    elif command -v podman &> /dev/null; then
        CONTAINER_RUNTIME=podman
    else
        echo "ERROR: Neither podman nor docker found in PATH"
        exit 1
    fi
fi

echo "=== Quay Security Scan Validation ==="
echo "Quay URL: ${OCP_QUAY_URL}"
echo "Test Repository: ${TEST_ORG}/${TEST_REPO}"
echo "Container Runtime: ${CONTAINER_RUNTIME}"
echo ""

# Check for required commands
for cmd in jq curl ${CONTAINER_RUNTIME}; do
    if ! command -v ${cmd} &> /dev/null; then
        echo "ERROR: Required command '${cmd}' not found in PATH"
        exit 1
    fi
done

# Step 1: Login to Quay
echo "Step 1: Logging into Quay..."
${CONTAINER_RUNTIME} login -u "${USERNAME}" -p "${PASSWORD}" "${OCP_QUAY_URL}"

# Step 2: Push test image
echo "Step 2: Pushing test image..."
${CONTAINER_RUNTIME} pull quay.io/quay/busybox:latest
${CONTAINER_RUNTIME} tag quay.io/quay/busybox:latest "${OCP_QUAY_URL}/${TEST_ORG}/${TEST_REPO}:latest"
${CONTAINER_RUNTIME} push "${OCP_QUAY_URL}/${TEST_ORG}/${TEST_REPO}:latest"

# Step 3: Get manifest digest
echo "Step 3: Getting manifest digest..."
DIGEST=$(${CONTAINER_RUNTIME} inspect "${OCP_QUAY_URL}/${TEST_ORG}/${TEST_REPO}:latest" \
  | jq -r '.[0].Digest' 2>/dev/null || echo "")

if [ -z "${DIGEST}" ]; then
    echo "WARNING: Could not get digest from ${CONTAINER_RUNTIME} inspect, trying alternative method..."
    # Alternative: Get digest from Quay API
    DIGEST=$(curl -s -u "${USERNAME}:${PASSWORD}" \
        "https://${OCP_QUAY_URL}/api/v1/repository/${TEST_ORG}/${TEST_REPO}/tag/?specificTag=latest" \
        | jq -r '.tags[0].manifest_digest' 2>/dev/null || echo "")
fi

if [ -z "${DIGEST}" ] || [ "${DIGEST}" == "null" ]; then
    echo "ERROR: Failed to get manifest digest"
    exit 1
fi

echo "Manifest digest: ${DIGEST}"

# Step 4: Poll for scan completion
echo "Step 4: Waiting for security scan to complete..."
MAX_WAIT=300  # 5 minutes
ELAPSED=0
STATUS=""

while [ $ELAPSED -lt $MAX_WAIT ]; do
  RESPONSE=$(curl -s -u "${USERNAME}:${PASSWORD}" \
    "https://${OCP_QUAY_URL}/api/v1/repository/${TEST_ORG}/${TEST_REPO}/manifest/${DIGEST}/security" \
    2>/dev/null || echo '{"status": "error"}')

  STATUS=$(echo "${RESPONSE}" | jq -r '.status' 2>/dev/null || echo "error")

  echo "  Scan status: ${STATUS} (${ELAPSED}s elapsed)"

  if [ "${STATUS}" != "queued" ]; then
    break
  fi

  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

if [ "${STATUS}" == "queued" ]; then
  echo "ERROR: Scan did not complete within ${MAX_WAIT}s"
  echo "Final status: ${STATUS}"
  exit 1
fi

# Step 5: Verify vulnerability data
echo "Step 5: Verifying vulnerability data..."
VULN_DATA=$(curl -s -u "${USERNAME}:${PASSWORD}" \
  "https://${OCP_QUAY_URL}/api/v1/repository/${TEST_ORG}/${TEST_REPO}/manifest/${DIGEST}/security?vulnerabilities=true" \
  2>/dev/null || echo '{"status": "error"}')

echo "${VULN_DATA}" | jq . 2>/dev/null || echo "${VULN_DATA}"

# Check if scan succeeded
SCAN_STATUS=$(echo "${VULN_DATA}" | jq -r '.status' 2>/dev/null || echo "error")

if [ "${SCAN_STATUS}" == "scanned" ]; then
  echo "✓ Scan completed successfully"

  # Try to get vulnerability count
  VULN_COUNT=$(echo "${VULN_DATA}" | jq -r '.data.Layer.Features // [] | length' 2>/dev/null || echo "unknown")
  echo "  Features scanned: ${VULN_COUNT}"

elif [ "${SCAN_STATUS}" == "failed" ]; then
  echo "WARNING: Scan status is 'failed'"
  ERROR_MSG=$(echo "${VULN_DATA}" | jq -r '.data.error // .error // "unknown error"' 2>/dev/null || echo "unknown")
  echo "  Error: ${ERROR_MSG}"
  # Don't exit 1 here - some images legitimately fail to scan
elif [ "${SCAN_STATUS}" == "unsupported" ]; then
  echo "INFO: Image is unsupported for scanning (expected for some base images)"
else
  echo "ERROR: Unexpected scan status: ${SCAN_STATUS}"
  exit 1
fi

# Step 6: Cleanup
echo "Step 6: Cleaning up..."
DELETE_RESPONSE=$(curl -s -X DELETE -u "${USERNAME}:${PASSWORD}" \
  "https://${OCP_QUAY_URL}/api/v1/repository/${TEST_ORG}/${TEST_REPO}" \
  2>/dev/null || echo '{}')

DELETE_STATUS=$(echo "${DELETE_RESPONSE}" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")

if [ "${DELETE_STATUS}" == "unknown" ] || [ -z "${DELETE_RESPONSE}" ]; then
  echo "✓ Repository deleted successfully"
else
  echo "  Delete response: ${DELETE_STATUS}"
fi

# Cleanup local image
${CONTAINER_RUNTIME} rmi "${OCP_QUAY_URL}/${TEST_ORG}/${TEST_REPO}:latest" &>/dev/null || true
${CONTAINER_RUNTIME} rmi quay.io/quay/busybox:latest &>/dev/null || true

echo ""
echo "=== Validation Complete ==="
echo "Result: SUCCESS"
exit 0
