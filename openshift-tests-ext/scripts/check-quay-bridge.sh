#!/bin/bash
set -euxo pipefail
shopt -s inherit_errexit 2>/dev/null || true

if [[ -z "${KUBECONFIG:-}" ]]; then
    echo "KUBECONFIG not set, skipping" >&2
    exit 2
fi

declare csvName
csvName=$(oc get csv --all-namespaces --no-headers 2>/dev/null | grep "quay-bridge-operator" | head -1 | awk '{print $2}')
if [[ -z "${csvName}" ]]; then
    echo "WARN: Quay Bridge operator CSV not found — bridge may not be deployed" >&2
    exit 2
fi

declare csvPhase
csvPhase=$(oc get csv --all-namespaces -o jsonpath="{.items[?(@.metadata.name==\"${csvName}\")].status.phase}" 2>/dev/null | awk '{print $1}')
if [[ "${csvPhase}" != "Succeeded" ]]; then
    echo "FAIL: Quay Bridge operator CSV is not Succeeded (phase: ${csvPhase})" >&2
    exit 1
fi

echo "PASS: Quay Bridge operator is installed (${csvName})"
exit 0
