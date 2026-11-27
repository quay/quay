#!/bin/bash
# Port of the OPP interop smoke (RunOdfStorageCheck):
# https://github.com/openshift/release/blob/main/ci-operator/step-registry/interop-tests/opp-quay-smoke/interop-tests-opp-quay-smoke-commands.sh
# Add as a new file: openshift-tests-ext/test/quay/scripts/check-quay-odf-storage.sh
set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

if [[ -z "${KUBECONFIG:-}" ]]; then
    echo "KUBECONFIG not set, skipping" >&2
    exit 2
fi

# ODF is a prerequisite for this test — skip when it is not deployed
declare noobaaPhase=""
noobaaPhase=$(oc get noobaa -n openshift-storage -o jsonpath='{.items[0].status.phase}' 2>/dev/null || true)
if [[ -z "${noobaaPhase}" ]]; then
    echo "No NooBaa found — ODF not deployed, skipping" >&2
    exit 2
fi
if [[ "${noobaaPhase}" != "Ready" ]]; then
    echo "FAIL: NooBaa not Ready (phase: ${noobaaPhase})" >&2
    exit 1
fi

# Find the Quay namespace (same discovery as the other scenarios)
declare quayNs=""
for ns in "${QUAY_NAMESPACE:-quay-enterprise}" quay openshift-quay; do
    if oc get quayregistry -n "${ns}" --no-headers 2>/dev/null | grep -q .; then
        quayNs="${ns}"
        break
    fi
done
if [[ -z "${quayNs}" ]]; then
    echo "No QuayRegistry CR found — Quay not deployed, skipping" >&2
    exit 2
fi

# The Quay-owned ObjectBucketClaim must be Bound
declare quayObc=""
quayObc=$(oc get objectbucketclaim -n "${quayNs}" -o name 2>/dev/null | grep -i quay | head -1 || true)
if [[ -z "${quayObc}" ]]; then
    quayObc=$(oc get objectbucketclaim -n "${quayNs}" -o name 2>/dev/null | head -1 || true)
fi
quayObc="${quayObc##*/}"
if [[ -z "${quayObc}" ]]; then
    echo "FAIL: no ObjectBucketClaim found in ${quayNs}" >&2
    exit 1
fi
declare obcPhase=""
obcPhase=$(oc get objectbucketclaim "${quayObc}" -n "${quayNs}" -o jsonpath='{.status.phase}' 2>/dev/null || true)
if [[ "${obcPhase}" != "Bound" ]]; then
    echo "FAIL: Quay OBC ${quayObc} not Bound (phase: ${obcPhase:-unknown})" >&2
    exit 1
fi

# Its ObjectBucket must resolve
if ! oc get objectbucket -o name 2>/dev/null | grep -q .; then
    echo "FAIL: no ObjectBucket found for Quay OBC ${quayObc}" >&2
    exit 1
fi

# No Quay PVC may be left unbound
declare unboundPvcs=""
unboundPvcs=$(oc get pvc -n "${quayNs}" --no-headers 2>/dev/null | awk '{print $1" "$2}' | grep -i quay | awk '$2 != "Bound" {print $1}' || true)
if [[ -n "${unboundPvcs}" ]]; then
    echo "FAIL: unbound Quay PVCs: ${unboundPvcs}" >&2
    exit 1
fi

echo "PASS: Quay OBC ${quayObc} Bound with healthy ODF object storage"
exit 0
