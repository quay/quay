#!/bin/bash
set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

if [[ -z "${KUBECONFIG:-}" ]]; then
    echo "KUBECONFIG not set, skipping" >&2
    exit 2
fi

declare namespace="${QUAY_NAMESPACE:-quay-enterprise}"

if ! oc get namespace "${namespace}" &>/dev/null; then
    declare altNamespace="quay-operator"
    if oc get namespace "${altNamespace}" &>/dev/null; then
        namespace="${altNamespace}"
    else
        echo "FAIL: Quay namespace not found (tried ${namespace} and quay-operator)" >&2
        exit 1
    fi
fi

# Single observation: fetch QuayRegistry list once and derive both existence
# and the Available condition from that snapshot to avoid a race between two oc calls.
declare quayJson=""
declare quayListRc=0
quayJson=$(oc get quayregistry -n "${namespace}" -o json 2>/dev/null) || quayListRc=$?
if (( quayListRc != 0 )); then
    declare quayPods
    quayPods=$(oc get pods -n "${namespace}" --no-headers --field-selector=status.phase=Running 2>/dev/null | wc -l | tr -d ' ')
    echo "FAIL: could not list QuayRegistry CRs in ${namespace} (oc exit ${quayListRc}; ${quayPods} running pods; CRD may be absent)" >&2
    exit 1
fi

# Existence: only a successful empty list proceeds to skip.
declare quayCount=0
if command -v python3 >/dev/null 2>&1; then
    quayCount=$(printf '%s' "${quayJson}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get("items", [])))' 2>/dev/null || echo 0)
else
    # Fallback: look for an item entry; items with at least one object contain '"metadata"'
    if printf '%s' "${quayJson}" | grep -q '"items"[[:space:]]*:[[:space:]]*\[[[:space:]]*{'; then
        quayCount=1
    else
        quayCount=0
    fi
fi
if (( quayCount == 0 )); then
    echo "No QuayRegistry CR found in ${namespace}" >&2
    exit 2
fi

declare quayStatus=""
if command -v python3 >/dev/null 2>&1; then
    quayStatus=$(printf '%s' "${quayJson}" | python3 -c '
import json, sys
d=json.load(sys.stdin)
items=d.get("items", [])
if not items:
    print("NotFound")
else:
    conds=items[0].get("status", {}).get("conditions", [])
    v="NotFound"
    for c in conds:
        if c.get("type") == "Available":
            v=c.get("status", "NotFound")
            break
    print(v)
' 2>/dev/null || echo "NotFound")
else
    # Grep fallback: try type->status then status->type
    quayStatus=$(printf '%s' "${quayJson}" | grep -o '"type"[[:space:]]*:[[:space:]]*"Available"[[:space:]]*,[[:space:]]*"status"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
    if [[ -z "${quayStatus}" ]]; then
        quayStatus=$(printf '%s' "${quayJson}" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"[[:space:]]*,[[:space:]]*"type"[[:space:]]*:[[:space:]]*"Available"' | head -1 | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
    fi
    if [[ -z "${quayStatus}" ]]; then
        quayStatus="NotFound"
    fi
fi

if [[ "${quayStatus}" != "True" ]]; then
    declare quayPods
    quayPods=$(oc get pods -n "${namespace}" --no-headers --field-selector=status.phase=Running 2>/dev/null | wc -l | tr -d ' ')
    echo "FAIL: QuayRegistry Available=${quayStatus} in ${namespace} (${quayPods} running pods; a namespace-wide pod count is not evidence the registry is operational)" >&2
    exit 1
fi

echo "PASS: Quay registry is operational in ${namespace}"
exit 0
