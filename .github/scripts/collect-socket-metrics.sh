#!/usr/bin/env bash
# Continuously polls the Pushgateway and appends gunicorn socket metrics
# to an output file. Each snapshot is labeled with the current test phase
# read from a phase file. Designed to run as a background process during CI.
#
# Usage:
#   METRICS_OUTPUT=path/to/metrics.txt PHASE_FILE=/tmp/metrics-phase.txt \
#     bash .github/scripts/collect-socket-metrics.sh &
#
# Update the phase by writing to $PHASE_FILE:
#   echo "database_auth_tests" > /tmp/metrics-phase.txt

set -u

PUSHGATEWAY_URL="${PUSHGATEWAY_URL:-http://localhost:9091/metrics}"
METRICS_OUTPUT="${METRICS_OUTPUT:-socket-metrics/metrics.txt}"
PHASE_FILE="${PHASE_FILE:-/tmp/metrics-phase.txt}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

mkdir -p "$(dirname "$METRICS_OUTPUT")"

echo "=== Socket Metrics Collection Started ===" > "$METRICS_OUTPUT"
echo "poll_interval=${POLL_INTERVAL}s" >> "$METRICS_OUTPUT"
echo "" >> "$METRICS_OUTPUT"

while true; do
    phase="unknown"
    if [ -f "$PHASE_FILE" ]; then
        phase=$(cat "$PHASE_FILE" 2>/dev/null || echo "unknown")
    fi

    metrics=$(curl -sf "$PUSHGATEWAY_URL" 2>/dev/null)
    if [ $? -eq 0 ]; then
        filtered=$(echo "$metrics" | grep -E 'gunicorn_socket|system_metrics_collector' | grep -v '^#')
        if [ -n "$filtered" ]; then
            {
                echo "--- phase=${phase} elapsed=$(date -u +%H:%M:%S) ---"
                echo "$filtered"
                echo ""
            } >> "$METRICS_OUTPUT"
        fi
    fi

    sleep "$POLL_INTERVAL"
done
