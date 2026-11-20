#!/bin/bash
# Port of the OPP interop smoke (RunAcsScan + RegisterQuayInAcs/RequestAcsScan):
# https://github.com/openshift/release/blob/main/ci-operator/step-registry/interop-tests/opp-quay-smoke/interop-tests-opp-quay-smoke-commands.sh
# Add as a new file: openshift-tests-ext/test/quay/scripts/check-quay-acs-scan.sh
set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

declare authFile="" initPayload="" regPayload="" scanPayload=""
trap 'rm -f "${authFile:-}" "${initPayload:-}" "${regPayload:-}" "${scanPayload:-}"' EXIT

if [[ -z "${KUBECONFIG:-}" ]]; then
    echo "KUBECONFIG not set, skipping" >&2
    exit 2
fi
command -v skopeo >/dev/null 2>&1 || {
    echo "FAIL: skopeo not in PATH — composite image needs it for push/pull" >&2
    exit 1
}

# ACS is optional in the bundle — skip when Central is not deployed
declare acsHost=""
acsHost=$(oc get route -n stackrox central -o jsonpath='{.spec.host}' 2>/dev/null || true)
if [[ -z "${acsHost}" ]]; then
    echo "ACS Central route not found — ACS not deployed, skipping" >&2
    exit 2
fi
declare acsPass=""
acsPass=$(oc get secret -n stackrox central-htpasswd -o jsonpath='{.data.password}' 2>/dev/null | base64 -d 2>/dev/null || true)
if [[ -z "${acsPass}" ]]; then
    echo "ACS admin password not available, skipping" >&2
    exit 2
fi

# --- Discover Quay, obtain credentials, ensure an image is pushed -----
# Same preamble as check-quay-push-pull.sh: scenarios run as separate
# processes, so this test stands alone. A shared lib sourced by both
# scripts would dedupe this if you prefer.
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
    initPayload=$(mktemp)
    chmod 600 "${initPayload}"
    printf '{"username":"quayadmin","password":"%s","email":"quayadmin@example.com","access_token":true}' "${quayPass}" > "${initPayload}"
    initResult=$(curl -sk --connect-timeout 15 --max-time 60 -X POST "https://${quayHost}/api/v1/user/initialize" \
        -H "Content-Type: application/json" \
        --data @"${initPayload}" 2>/dev/null || true)
    rm -f "${initPayload}"
    quayToken=$(printf '%s' "${initResult}" | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || true)
    [[ -n "${quayToken}" ]] && quayUser="quayadmin"
fi
if [[ -z "${quayToken}" && -z "${quayPass}" ]]; then
    echo "FAIL: could not obtain Quay credentials from any source" >&2
    exit 1
fi
if [[ -n "${quayToken}" ]]; then
    curl -sk --connect-timeout 15 --max-time 60 -X POST "https://${quayHost}/api/v1/organization/" \
        -K <(printf 'header = "Authorization: Bearer %s"\n' "${quayToken}") -H "Content-Type: application/json" \
        -d '{"name":"interop-smoke-test","email":"interop-test@example.com"}' >/dev/null 2>&1 || true
else
    curl -sk --connect-timeout 15 --max-time 60 -X POST "https://${quayHost}/api/v1/organization/" \
        -K <(printf 'user = "%s:%s"\n' "${quayUser}" "${quayPass}") -H "Content-Type: application/json" \
        -d '{"name":"interop-smoke-test","email":"interop-test@example.com"}' >/dev/null 2>&1 || true
fi

# Own tag so this scenario never races the push/pull scenario
declare pushTarget="${quayHost}/interop-smoke-test/ubi-smoke:acs"
authFile=$(mktemp)
if [[ -n "${quayToken}" ]]; then
    printf '{"auths":{"%s":{"auth":"%s"}}}\n' "${quayHost}" "$(echo -n "\$oauthtoken:${quayToken}" | base64 -w0)" > "${authFile}"
else
    printf '{"auths":{"%s":{"auth":"%s"}}}\n' "${quayHost}" "$(echo -n "${quayUser}:${quayPass}" | base64 -w0)" > "${authFile}"
fi
skopeo copy --dest-tls-verify=false --dest-authfile="${authFile}" \
    docker://registry.access.redhat.com/ubi9-minimal:latest "docker://${pushTarget}" >/dev/null 2>&1 || {
    echo "FAIL: could not push ${pushTarget} for ACS to scan" >&2
    exit 1
}

# --- Register Quay as an ACS image integration (idempotent) ------------
declare response=""
response=$(curl -sk --connect-timeout 15 --max-time 60 -K <(printf 'user = "admin:%s"\n' "${acsPass}") "https://${acsHost}/v1/imageintegrations" 2>/dev/null || true)
if ! printf '%s' "${response}" | grep -q "${quayHost}"; then
    declare regUser="" regPass=""
    if [[ -n "${quayToken}" ]]; then regUser="\$oauthtoken"; regPass="${quayToken}"; else regUser="${quayUser}"; regPass="${quayPass}"; fi
    regPayload=$(mktemp)
    chmod 600 "${regPayload}"
    printf '{"name":"interop-quay-smoke","type":"docker","categories":["REGISTRY"],"docker":{"endpoint":"%s","username":"%s","password":"%s","insecure":true},"skipTestIntegration":true}' "${quayHost}" "${regUser}" "${regPass}" > "${regPayload}"
    declare regCode=""
    regCode=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 15 --max-time 60 \
        -X POST "https://${acsHost}/v1/imageintegrations" -K <(printf 'user = "admin:%s"\n' "${acsPass}") \
        -H "Content-Type: application/json" --data @"${regPayload}" 2>/dev/null || echo 000)
    rm -f "${regPayload}"
    if [[ "${regCode}" != 2* ]]; then
        echo "FAIL: could not register Quay in ACS (HTTP ${regCode})" >&2
        exit 1
    fi
fi

# --- Request a scan and poll until ACS reports the image ---------------
scanPayload=$(mktemp)
chmod 600 "${scanPayload}"
printf '{"imageName":"%s","force":true}' "${pushTarget}" > "${scanPayload}"
curl -sk --connect-timeout 15 --max-time 60 -X POST "https://${acsHost}/v1/images/scan" \
    -K <(printf 'user = "admin:%s"\n' "${acsPass}") -H "Content-Type: application/json" \
    --data @"${scanPayload}" >/dev/null 2>&1 || true
rm -f "${scanPayload}"

declare -i attempts=0
while (( attempts < 40 )); do
    declare scanResult=""
    scanResult=$(curl -sk --connect-timeout 15 --max-time 30 -K <(printf 'user = "admin:%s"\n' "${acsPass}") \
        "https://${acsHost}/v1/images?query=Image:${pushTarget}" 2>/dev/null || true)
    if printf '%s' "${scanResult}" | grep -q "${pushTarget}"; then
        echo "PASS: ACS scanned ${pushTarget}"
        exit 0
    fi
    attempts=$((attempts + 1))
    sleep 15
done
echo "FAIL: ACS did not detect the pushed image within 10 minutes" >&2
exit 1
