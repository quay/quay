#!/bin/bash
set -euxo pipefail
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

declare quayStatus
quayStatus=$(oc get quayregistry -n "${namespace}" -o jsonpath='{.items[0].status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "NotFound")

if [[ "${quayStatus}" != "True" ]]; then
    declare quayPods
    quayPods=$(oc get pods -n "${namespace}" --no-headers --field-selector=status.phase=Running 2>/dev/null | wc -l | tr -d ' ')
    if [[ "${quayPods}" -eq 0 ]]; then
        echo "FAIL: Quay registry not available and no running pods in ${namespace}" >&2
        exit 1
    fi
    echo "WARN: QuayRegistry CR status not Available, but ${quayPods} pods running" >&2
fi

echo "PASS: Quay registry is operational in ${namespace}"
exit 0
true
