#!/bin/bash
# Initialize Splunk with index and bearer token for Quay local dev
# This script runs inside the Splunk container via: docker exec quay-splunk bash /tmp/init-splunk.sh
set -e

SPLUNK_USER="admin"
SPLUNK_PASS="changeme1"
INDEX_NAME="quay_logs"
AUTH="${SPLUNK_USER}:${SPLUNK_PASS}"
BASE_URL="https://localhost:8089"
TOKEN_OUTPUT_FILE="/tmp/quay_splunk_bearer_token"

echo "Waiting for Splunk to be fully ready..."
timeout=120
while [ $timeout -gt 0 ]; do
    if curl -sf -k -u "${AUTH}" "${BASE_URL}/services/server/health/splunkd" &>/dev/null; then
        echo "Splunk is ready!"
        break
    fi
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "ERROR: Splunk failed to start within timeout"
    exit 1
fi

# 1. Create index for Quay logs
echo "Creating index '${INDEX_NAME}'..."
if curl -sf -k -u "${AUTH}" "${BASE_URL}/services/data/indexes/${INDEX_NAME}" &>/dev/null; then
    echo "  Index already exists, skipping"
else
    curl -sf -k -u "${AUTH}" "${BASE_URL}/services/data/indexes" \
        -d "name=${INDEX_NAME}" -d "datatype=event" >/dev/null
    echo "  Index created"
fi

# 2. Enable token authentication and create bearer token
echo "Enabling token authentication..."
curl -sf -k -u "${AUTH}" \
    "${BASE_URL}/services/admin/token-auth/tokens_auth" \
    -d "disabled=false" >/dev/null 2>&1 || true
sleep 5

# Check if we already have a saved token
if [ -f "${TOKEN_OUTPUT_FILE}" ]; then
    EXISTING_TOKEN=$(cat "${TOKEN_OUTPUT_FILE}")
    if [ -n "${EXISTING_TOKEN}" ]; then
        echo "  Bearer token already exists, skipping creation"
        BEARER_TOKEN="${EXISTING_TOKEN}"
    fi
fi

if [ -z "${BEARER_TOKEN:-}" ]; then
    echo "Creating bearer token..."
    BEARER_RESPONSE=$(curl -sf -k -u "${AUTH}" \
        "${BASE_URL}/services/authorization/tokens?output_mode=json" \
        -d "name=admin" \
        -d "audience=Quay" 2>/dev/null || echo "")

    BEARER_TOKEN=""
    if [ -n "${BEARER_RESPONSE}" ]; then
        BEARER_TOKEN=$(echo "${BEARER_RESPONSE}" | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d['entry'][0]['content']['token'])" 2>/dev/null || echo "")
    fi

    if [ -n "${BEARER_TOKEN}" ]; then
        echo "${BEARER_TOKEN}" > "${TOKEN_OUTPUT_FILE}"
        echo "  Bearer token created and saved"
    else
        echo "  WARNING: Could not create bearer token automatically."
        echo "  Create one manually: Splunk UI > Settings > Tokens > New Token"
    fi
fi

echo ""
echo "============================================="
echo "  Splunk Local Dev Setup Complete"
echo "============================================="
echo "  Web UI:     http://localhost:8000"
echo "  Username:   admin"
echo "  Password:   changeme1"
echo "  Index:      ${INDEX_NAME}"
echo "  Mgmt API:   https://localhost:8089"
if [ -n "${BEARER_TOKEN:-}" ]; then
echo "  SDK Token:  ${BEARER_TOKEN}"
fi
echo "============================================="
