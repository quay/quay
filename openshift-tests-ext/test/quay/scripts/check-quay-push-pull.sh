#!/bin/bash
# Port of the OPP interop smoke (RunPushPull + DiscoverQuay/GetQuayAuth/CreateTestOrg):
# https://github.com/openshift/release/blob/main/ci-operator/step-registry/interop-tests/opp-quay-smoke/interop-tests-opp-quay-smoke-commands.sh
set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

if [[ -z "${KUBECONFIG:-}" ]]; then
    echo "KUBECONFIG not set, skipping" >&2
    exit 2
fi
command -v skopeo >/dev/null 2>&1 || {
    echo "FAIL: skopeo not in PATH — composite image needs it for push/pull" >&2
    exit 1
}

# --- Discover the QuayRegistry and its route ---------------------------
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

declare quayHost=""
quayHost=$(oc get quayregistry -n "${quayNs}" -o jsonpath='{.items[0].status.registryEndpoint}')
quayHost="${quayHost#https://}"
if [[ -z "${quayHost}" ]]; then
    echo "FAIL: Quay registry endpoint not ready" >&2
    exit 1
fi

# --- Credentials: quayadmin secret -> quaydevel secret -> fresh admin --
declare quayUser="" quayPass="" quayToken=""
if oc get secret quayadmin -n "${quayNs}" &>/dev/null; then
    quayToken=$(oc get secret quayadmin -n "${quayNs}" -o jsonpath='{.data.token}' 2>/dev/null | base64 -d 2>/dev/null || true)
    quayPass=$(oc get secret quayadmin -n "${quayNs}" -o jsonpath='{.data.password}' 2>/dev/null | base64 -d 2>/dev/null || true)
    [[ -n "${quayToken}" || -n "${quayPass}" ]] && quayUser="quayadmin"
fi
if [[ -z "${quayToken}" && -z "${quayPass}" ]] && oc get secret quaydevel -n "${quayNs}" &>/dev/null; then
    quayPass=$(oc get secret quaydevel -n "${quayNs}" -o jsonpath='{.data.password}' 2>/dev/null | base64 -d 2>/dev/null || true)
    [[ -n "${quayPass}" ]] && quayUser="quaydevel"
fi
if [[ -z "${quayToken}" && -z "${quayPass}" ]]; then
    quayPass=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20 || true)
    declare initResult=""
    initResult=$(curl -sk --connect-timeout 15 --max-time 60 -X POST "https://${quayHost}/api/v1/user/initialize" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"quayadmin\",\"password\":\"${quayPass}\",\"email\":\"quayadmin@example.com\",\"access_token\":true}" 2>/dev/null || true)
    quayToken=$(printf '%s' "${initResult}" | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
    [[ -n "${quayToken}" ]] && quayUser="quayadmin"
fi
if [[ -z "${quayToken}" && -z "${quayPass}" ]]; then
    echo "FAIL: could not obtain Quay credentials from any source" >&2
    exit 1
fi

declare -a authArgs=()
if [[ -n "${quayToken}" ]]; then
    authArgs=(-H "Authorization: Bearer ${quayToken}")
else
    authArgs=(-u "${quayUser}:${quayPass}")
fi

# --- Create the test organization (idempotent) -------------------------
curl -sk --connect-timeout 15 --max-time 60 -X POST "https://${quayHost}/api/v1/organization/" \
    "${authArgs[@]}" -H "Content-Type: application/json" \
    -d '{"name":"interop-smoke-test","email":"interop-test@example.com"}' >/dev/null 2>&1 || true

# --- Push ubi9-minimal into Quay, then verify it pulls back out --------
declare pushTarget="${quayHost}/interop-smoke-test/ubi-smoke:interop"
declare authFile=""
authFile=$(mktemp)
trap 'rm -f "${authFile}"' EXIT
if [[ -n "${quayToken}" ]]; then
    printf '{"auths":{"%s":{"auth":"%s"}}}\n' "${quayHost}" "$(echo -n "\$oauthtoken:${quayToken}" | base64 -w0)" > "${authFile}"
else
    printf '{"auths":{"%s":{"auth":"%s"}}}\n' "${quayHost}" "$(echo -n "${quayUser}:${quayPass}" | base64 -w0)" > "${authFile}"
fi

if ! skopeo copy --dest-tls-verify=false --dest-authfile="${authFile}" \
        docker://registry.access.redhat.com/ubi9-minimal:latest "docker://${pushTarget}"; then
    echo "FAIL: skopeo push to Quay failed" >&2
    exit 1
fi
if ! skopeo inspect --tls-verify=false --authfile="${authFile}" "docker://${pushTarget}" >/dev/null; then
    echo "FAIL: image not pullable from Quay after push" >&2
    exit 1
fi

echo "PASS: pushed and pulled ${pushTarget}"
exit 0
