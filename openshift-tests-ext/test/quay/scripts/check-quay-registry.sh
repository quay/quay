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
declare quayListErr=""
declare quayListErrFile
quayListErrFile=$(mktemp)
trap 'rm -f "${quayListErrFile:-}"' EXIT
quayJson=$(oc get quayregistry -n "${namespace}" -o json 2>"${quayListErrFile}") || quayListRc=$?
quayListErr=$(cat "${quayListErrFile}" 2>/dev/null || true)
rm -f "${quayListErrFile}"
trap - EXIT
if (( quayListRc != 0 )); then
    declare quayPods
    quayPods=$(oc get pods -n "${namespace}" --no-headers --field-selector=status.phase=Running 2>/dev/null | wc -l | tr -d ' ' || true)
    echo "FAIL: could not list QuayRegistry CRs in ${namespace} (oc exit ${quayListRc}: ${quayListErr}; ${quayPods} running pods; CRD may be absent)" >&2
    exit 1
fi

# JSON parsing requires python3: fail closed instead of flaky grep fallback (false-skips).
if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: python3 is required to parse QuayRegistry JSON (not in PATH)" >&2
    exit 1
fi

# Existence: only a successful empty list proceeds to skip.
declare quayCount=0
declare quayCountErr=""
declare quayCountErrFile
quayCountErrFile=$(mktemp)
trap 'rm -f "${quayCountErrFile:-}"' EXIT
if ! quayCount=$(printf '%s' "${quayJson}" | python3 -c '
import json, sys
try:
    d=json.load(sys.stdin)
except Exception as e:
    print(f"json parse error: {e}", file=sys.stderr)
    sys.exit(1)
if "items" not in d:
    print("missing \"items\" key in QuayRegistry list JSON", file=sys.stderr)
    sys.exit(1)
items=d["items"]
if not isinstance(items, list):
    print(f"\"items\" value is not a list: {type(items).__name__}", file=sys.stderr)
    sys.exit(1)
print(len(items))
' 2>"${quayCountErrFile}"); then
    quayCountErr=$(cat "${quayCountErrFile}" 2>/dev/null || true)
    echo "FAIL: could not parse QuayRegistry list JSON in ${namespace}: ${quayCountErr}" >&2
    rm -f "${quayCountErrFile}"
    trap - EXIT
    exit 1
fi
rm -f "${quayCountErrFile}"
trap - EXIT
if (( quayCount == 0 )); then
    echo "No QuayRegistry CR found in ${namespace}" >&2
    exit 2
fi

declare quayStatus=""
declare quayStatusErr=""
declare quayStatusErrFile
quayStatusErrFile=$(mktemp)
trap 'rm -f "${quayStatusErrFile:-}"' EXIT
if ! quayStatus=$(printf '%s' "${quayJson}" | python3 -c '
import json, sys
try:
    d=json.load(sys.stdin)
except Exception as e:
    print(f"json parse error: {e}", file=sys.stderr)
    sys.exit(1)
if "items" not in d:
    print("missing \"items\" key in QuayRegistry list JSON", file=sys.stderr)
    sys.exit(1)
items=d["items"]
if not isinstance(items, list):
    print(f"\"items\" value is not a list: {type(items).__name__}", file=sys.stderr)
    sys.exit(1)
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
' 2>"${quayStatusErrFile}"); then
    quayStatusErr=$(cat "${quayStatusErrFile}" 2>/dev/null || true)
    echo "FAIL: could not parse QuayRegistry Available condition in ${namespace}: ${quayStatusErr}" >&2
    rm -f "${quayStatusErrFile}"
    trap - EXIT
    exit 1
fi
rm -f "${quayStatusErrFile}"
trap - EXIT

if [[ "${quayStatus}" != "True" ]]; then
    declare quayPods
    quayPods=$(oc get pods -n "${namespace}" --no-headers --field-selector=status.phase=Running 2>/dev/null | wc -l | tr -d ' ' || true)
    echo "FAIL: QuayRegistry Available=${quayStatus} in ${namespace} (${quayPods} running pods; a namespace-wide pod count is not evidence the registry is operational)" >&2
    exit 1
fi

echo "PASS: Quay registry is operational in ${namespace}"
exit 0
