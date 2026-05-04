#!/usr/bin/env bash
set -euo pipefail

# Provision an ephemeral OpenShift cluster via the OpenShift CI Gangway API.
# Claims a cluster from a Hive ClusterPool, downloads kubeconfig, validates.
#
# Usage: cluster-provision.sh [up|down|status] [KUBECONFIG_PATH] [OCP_VERSION]

ACTION="${1:-status}"
KUBECONFIG_OUT="${2:-/tmp/k}"
OCP_VERSION="${3:-4.18}"

GANGWAY_BASE="https://gangway-ci.apps.ci.l2s4.p1.openshiftapps.com"
JOB_NAME="periodic-ci-quay-quay-master-claim-claim-cluster"
STATE_DIR="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/cluster-provision-${UID}"
STATE_FILE="${STATE_DIR}/state.json"

POLL_INTERVAL_INITIAL=15
POLL_INTERVAL_MAX=60
POLL_TIMEOUT=2400 # 40 minutes

GCSWEB_BASE="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs"
ARTIFACT_SUBPATH="artifacts/claim-cluster/export-kubeconfig/artifacts/kubeconfig.enc"
ENCRYPTION_KEY="${KUBECONFIG_ENCRYPTION_KEY:-}"

CURL_CONNECT_TIMEOUT=10
CURL_MAX_TIME=30

die() {
  echo "ERROR: $*" >&2
  exit 1
}
info() { echo "==> $*"; }

epoch_now() { date +%s; }
iso_now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

epoch_from_iso() {
  local ts="$1"
  if date -d "$ts" +%s 2>/dev/null; then
    return
  fi
  date -j -f "%Y-%m-%dT%H:%M:%SZ" "$ts" +%s 2>/dev/null || echo "0"
}

check_prereqs() {
  if [[ -z "${GANGWAY_TOKEN:-}" ]]; then
    echo "GANGWAY_TOKEN is not set."
    echo ""
    echo "To obtain a token:"
    echo "  1. Log in to the OpenShift CI cluster:"
    echo "     oc login https://api.ci.l2s4.p1.openshiftapps.com:6443 --web"
    echo "  2. Get your token:"
    echo "     oc whoami -t"
    echo "  3. Export it:"
    echo "     export GANGWAY_TOKEN=\$(oc whoami -t)"
    echo ""
    echo "For a permanent token, join the appropriate Rover group."
    exit 1
  fi
  if [[ -z "${ENCRYPTION_KEY}" ]]; then
    echo "KUBECONFIG_ENCRYPTION_KEY is not set."
    echo ""
    echo "This is the passphrase used to decrypt the cluster kubeconfig."
    echo "Contact the Quay CI team for access."
    exit 1
  fi
  for cmd in curl jq openssl; do
    command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' is required but not found on PATH"
  done
}

gangway_post() {
  local endpoint="$1" payload="$2"
  local http_code body tmpfile
  tmpfile=$(mktemp)
  if ! http_code=$(curl -s -w "%{http_code}" -o "$tmpfile" \
    --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" \
    -X POST \
    -H "Authorization: Bearer ${GANGWAY_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "${GANGWAY_BASE}${endpoint}"); then
    body=$(cat "$tmpfile" 2>/dev/null || true)
    rm -f "$tmpfile"
    die "Gangway API POST ${endpoint} transport error: ${body}"
  fi
  body=$(cat "$tmpfile")
  rm -f "$tmpfile"

  if [[ "$http_code" == "401" ]]; then
    die "Authentication failed (HTTP 401). Your GANGWAY_TOKEN may be expired. Re-run: oc login ... && export GANGWAY_TOKEN=\$(oc whoami -t)"
  fi
  if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
    die "Gangway API POST ${endpoint} failed (HTTP ${http_code}): ${body}"
  fi
  echo "$body"
}

gangway_get() {
  local endpoint="$1"
  local http_code body tmpfile attempt
  for attempt in 1 2 3; do
    tmpfile=$(mktemp)
    if ! http_code=$(curl -s -w "%{http_code}" -o "$tmpfile" \
      --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" \
      -H "Authorization: Bearer ${GANGWAY_TOKEN}" \
      "${GANGWAY_BASE}${endpoint}"); then
      body=$(cat "$tmpfile" 2>/dev/null || true)
      rm -f "$tmpfile"
      die "Gangway API GET ${endpoint} transport error: ${body}"
    fi
    body=$(cat "$tmpfile")
    rm -f "$tmpfile"

    if [[ "$http_code" == "429" ]]; then
      info "Gangway rate-limited (429) — backing off 90s (attempt ${attempt}/3)..."
      sleep 90
      continue
    fi
    if [[ "$http_code" == "401" ]]; then
      die "Authentication failed (HTTP 401). Your GANGWAY_TOKEN may be expired. Re-run: oc login ... && export GANGWAY_TOKEN=\$(oc whoami -t)"
    fi
    if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
      die "Gangway API GET ${endpoint} failed (HTTP ${http_code}): ${body}"
    fi
    echo "$body"
    return 0
  done
  die "Gangway API GET ${endpoint} failed after 3 attempts (rate limited)"
}

save_state() {
  [[ -L "$STATE_DIR" ]] && die "Refusing to write through symlinked state dir: $STATE_DIR"
  [[ -L "$STATE_FILE" ]] && die "Refusing to write through symlinked state file: $STATE_FILE"
  mkdir -p "$STATE_DIR"
  chmod 700 "$STATE_DIR"
  jq -n \
    --arg eid "$1" \
    --arg gcs "$2" \
    --arg url "$3" \
    --arg kfg "$4" \
    --arg sta "$5" \
    --arg sts "$6" \
    '{execution_id: $eid, gcs_path: $gcs, job_url: $url, kubeconfig_path: $kfg, started_at: $sta, status: $sts}' \
    >"$STATE_FILE"
}

update_state_field() {
  local field="$1" value="$2"
  if [[ -f "$STATE_FILE" ]]; then
    [[ -L "$STATE_DIR" ]] && die "Refusing to write through symlinked state dir: $STATE_DIR"
    [[ -L "$STATE_FILE" ]] && die "Refusing to write through symlinked state file: $STATE_FILE"
    local tmpfile
    tmpfile=$(mktemp "${STATE_DIR}/.state.XXXXXX")
    jq --arg f "$field" --arg v "$value" '.[$f] = $v' "$STATE_FILE" >"$tmpfile"
    mv "$tmpfile" "$STATE_FILE"
  fi
}

gcs_from_url() {
  local job_url="$1"
  echo "$job_url" | sed -n 's|.*/view/gs/||p'
}

try_download_kubeconfig() {
  local gcs_root="$1"
  local url response_meta http_code content_type tmpfile
  url="${GCSWEB_BASE}/${gcs_root}/${ARTIFACT_SUBPATH}"
  tmpfile=$(mktemp)
  if ! response_meta=$(curl -s -w "%{http_code}|%{content_type}" -o "$tmpfile" \
    --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time 60 \
    "$url"); then
    rm -f "$tmpfile"
    return 1
  fi
  http_code="${response_meta%%|*}"
  content_type="${response_meta#*|}"
  # gcsweb returns 200+HTML for missing files; only proceed for binary content
  if [[ "$http_code" == "200" ]] && [[ "$content_type" != *"text/html"* ]] && [[ -s "$tmpfile" ]]; then
    mkdir -p "$(dirname "$KUBECONFIG_OUT")"
    if openssl enc -d -aes-256-cbc -pbkdf2 \
      -pass pass:"${ENCRYPTION_KEY}" \
      -in "$tmpfile" \
      -out "${KUBECONFIG_OUT}"; then
      chmod 600 "$KUBECONFIG_OUT"
      rm -f "$tmpfile"
      return 0
    else
      echo "WARNING: Failed to decrypt kubeconfig. Wrong KUBECONFIG_ENCRYPTION_KEY?" >&2
      rm -f "$tmpfile"
      return 1
    fi
  fi
  rm -f "$tmpfile"
  return 1
}

ensure_oc() {
  if command -v oc >/dev/null 2>&1; then
    return 0
  fi
  info "oc not found — installing..."
  local arch tmpdir tarball
  arch=$(uname -m)
  case "$arch" in
    x86_64) arch="amd64" ;;
    aarch64) arch="arm64" ;;
    *)
      echo "WARNING: unsupported arch $arch — skipping oc install"
      return 1
      ;;
  esac
  tmpdir=$(mktemp -d)
  tarball="${tmpdir}/oc.tar.gz"
  if curl -sL --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time 120 \
    -o "$tarball" \
    "https://mirror.openshift.com/pub/openshift-v4/${arch}/clients/ocp/stable/openshift-client-linux.tar.gz"; then
    tar -xzf "$tarball" -C "$tmpdir" oc 2>/dev/null
    if [[ -x "${tmpdir}/oc" ]]; then
      mv "${tmpdir}/oc" /usr/local/bin/oc 2>/dev/null || mv "${tmpdir}/oc" "${HOME}/.local/bin/oc" 2>/dev/null || {
        export PATH="${tmpdir}:${PATH}"
        info "oc installed to ${tmpdir}/oc (added to PATH)"
        return 0
      }
      info "oc installed to $(command -v oc)"
    else
      echo "WARNING: failed to extract oc from tarball"
      rm -rf "$tmpdir"
      return 1
    fi
  else
    echo "WARNING: failed to download oc binary"
    rm -rf "$tmpdir"
    return 1
  fi
  rm -f "$tarball"
}

validate_cluster() {
  ensure_oc || true
  if ! command -v oc >/dev/null 2>&1; then
    echo "WARNING: could not install 'oc' — skipping cluster validation."
    return
  fi
  local server
  server=$(oc --kubeconfig="$KUBECONFIG_OUT" whoami --show-server 2>/dev/null || true)
  if [[ -n "$server" ]]; then
    info "Cluster validated — server: ${server}"
  else
    echo "WARNING: Could not validate cluster connectivity. The kubeconfig was downloaded but 'oc whoami --show-server' failed."
  fi
}

poll_and_download() {
  local exec_id="$1"
  local job_url="$2"
  local gcs_root start_epoch interval status elapsed response live_url

  gcs_root=$(gcs_from_url "$job_url")
  start_epoch=$(epoch_now)
  interval=$POLL_INTERVAL_INITIAL

  info "Polling for cluster readiness (timeout: ${POLL_TIMEOUT}s)..."

  while true; do
    elapsed=$(($(epoch_now) - start_epoch))
    if ((elapsed > POLL_TIMEOUT)); then
      die "Timed out after ${POLL_TIMEOUT}s waiting for cluster. Check job: ${job_url}"
    fi

    response=$(gangway_get "/v1/executions/${exec_id}")
    status=$(echo "$response" | jq -r '.job_status // empty')

    # Gangway may not return job_url at trigger time; pick it up from poll responses
    if [[ -z "$gcs_root" ]]; then
      live_url=$(echo "$response" | jq -r '.job_url // empty')
      if [[ -n "$live_url" ]]; then
        job_url="$live_url"
        gcs_root=$(gcs_from_url "$job_url")
        update_state_field "job_url" "$job_url"
        info "Job URL: ${job_url}"
      fi
    fi

    update_state_field "status" "$status"

    case "$status" in
      FAILURE | ERROR | ABORTED)
        die "Job ended with status ${status}. Check: ${job_url}"
        ;;
    esac

    if [[ -n "$gcs_root" ]] && try_download_kubeconfig "$gcs_root"; then
      update_state_field "status" "READY"
      info "Kubeconfig downloaded to ${KUBECONFIG_OUT}"
      validate_cluster
      echo ""
      echo "=== Cluster Ready ==="
      echo "Kubeconfig: ${KUBECONFIG_OUT}"
      echo "Usage:      export KUBECONFIG=${KUBECONFIG_OUT}"
      echo "            oc whoami"
      echo "Job URL:    ${job_url}"
      echo "Note:       Cluster auto-expires in ~4 hours"
      return 0
    fi

    info "Status: ${status} | Elapsed: ${elapsed}s | Next check in ${interval}s"
    sleep "$interval"
    if ((interval < POLL_INTERVAL_MAX)); then
      interval=$POLL_INTERVAL_MAX
    fi
  done
}

up() {
  check_prereqs

  if [[ -f "$STATE_FILE" ]]; then
    [[ -L "$STATE_FILE" ]] && die "Refusing to read symlinked state file: $STATE_FILE"
    local existing_id existing_status existing_job_url
    existing_id=$(jq -r '.execution_id // empty' "$STATE_FILE")
    existing_status=$(jq -r '.status // empty' "$STATE_FILE")

    if [[ -n "$existing_id" && "$existing_status" != "FAILURE" && "$existing_status" != "ERROR" && "$existing_status" != "ABORTED" ]]; then
      info "Found existing execution ${existing_id} (status: ${existing_status}). Resuming..."
      existing_job_url=$(jq -r '.job_url // empty' "$STATE_FILE")
      update_state_field "kubeconfig_path" "$KUBECONFIG_OUT"
      poll_and_download "$existing_id" "$existing_job_url"
      return $?
    fi
  fi

  info "Triggering cluster claim via Gangway..."
  local payload response exec_id gcs_path job_url job_status
  payload=$(jq -n '{
        job_name: $job,
        job_execution_type: "1",
        pod_spec_options: { envs: { OCP_VERSION: $ocp } }
    }' --arg job "$JOB_NAME" --arg ocp "$OCP_VERSION")

  response=$(gangway_post "/v1/executions" "$payload")

  exec_id=$(echo "$response" | jq -r '.id // empty')
  gcs_path=$(echo "$response" | jq -r '.gcs_path // empty')
  job_url=$(echo "$response" | jq -r '.job_url // empty')
  job_status=$(echo "$response" | jq -r '.job_status // empty')

  if [[ -z "$exec_id" ]]; then
    die "Failed to get execution ID from Gangway response: ${response}"
  fi

  info "Execution triggered: ${exec_id}"
  info "Job URL: ${job_url}"
  info "Initial status: ${job_status}"

  save_state "$exec_id" "$gcs_path" "$job_url" "$KUBECONFIG_OUT" "$(iso_now)" "$job_status"

  poll_and_download "$exec_id" "$job_url"
}

down() {
  command -v jq >/dev/null 2>&1 || die "'jq' is required but not found on PATH"
  if [[ -f "$STATE_FILE" ]]; then
    [[ -L "$STATE_FILE" ]] && die "Refusing to read symlinked state file: $STATE_FILE"
    local kubeconfig_path
    kubeconfig_path=$(jq -r '.kubeconfig_path // empty' "$STATE_FILE")
    info "Cleaning up state..."
    rm -f "$STATE_FILE"
    if [[ -n "$kubeconfig_path" && -f "$kubeconfig_path" ]]; then
      rm -f "$kubeconfig_path"
      info "Removed kubeconfig: ${kubeconfig_path}"
    fi
    rmdir "$STATE_DIR" 2>/dev/null || true
    info "Cleanup complete."
  else
    info "No active cluster provision found."
  fi
  echo ""
  echo "Note: Clusters auto-expire after ~4 hours via Hive. No explicit API teardown is needed."
}

status() {
  command -v jq >/dev/null 2>&1 || die "'jq' is required but not found on PATH"
  if [[ ! -f "$STATE_FILE" ]]; then
    echo "No active cluster provision."
    return 0
  fi

  [[ -L "$STATE_FILE" ]] && die "Refusing to read symlinked state file: $STATE_FILE"

  local state exec_id started_at cur_status kubeconfig_path job_url gcs_path
  state=$(cat "$STATE_FILE")
  exec_id=$(echo "$state" | jq -r '.execution_id // "unknown"')
  started_at=$(echo "$state" | jq -r '.started_at // "unknown"')
  cur_status=$(echo "$state" | jq -r '.status // "unknown"')
  kubeconfig_path=$(echo "$state" | jq -r '.kubeconfig_path // "unknown"')
  job_url=$(echo "$state" | jq -r '.job_url // "unknown"')
  gcs_path=$(echo "$state" | jq -r '.gcs_path // "unknown"')

  echo "=== Cluster Provision Status ==="
  echo "Execution ID:  ${exec_id}"
  echo "Started:       ${started_at}"
  echo "Cached Status: ${cur_status}"
  echo "Job URL:       ${job_url}"
  echo "GCS Path:      ${gcs_path}"
  echo "Kubeconfig:    ${kubeconfig_path}"

  if [[ "$started_at" != "unknown" ]]; then
    local start_epoch now_epoch elapsed remaining_s remaining_m
    start_epoch=$(epoch_from_iso "$started_at")
    now_epoch=$(epoch_now)
    elapsed=$((now_epoch - start_epoch))
    remaining_s=$((14400 - elapsed))
    if ((remaining_s > 0)); then
      remaining_m=$((remaining_s / 60))
      echo "Est. remaining: ~${remaining_m} minutes"
    else
      echo "Est. remaining: EXPIRED (started >4h ago)"
    fi
  fi

  if [[ -n "${GANGWAY_TOKEN:-}" && "$exec_id" != "unknown" ]]; then
    echo ""
    info "Fetching live status from Gangway..."
    local live_response live_status
    live_response=$(gangway_get "/v1/executions/${exec_id}" 2>/dev/null || true)
    if [[ -n "$live_response" ]]; then
      live_status=$(echo "$live_response" | jq -r '.job_status // empty')
      if [[ -n "$live_status" ]]; then
        echo "Live Status:   ${live_status}"
        update_state_field "status" "$live_status"
      fi
    fi
  fi

  if [[ -f "$kubeconfig_path" ]]; then
    ensure_oc
    if command -v oc >/dev/null 2>&1; then
      echo ""
      info "Testing cluster connectivity..."
      local server
      server=$(oc --kubeconfig="$kubeconfig_path" whoami --show-server 2>/dev/null || true)
      if [[ -n "$server" ]]; then
        echo "Cluster:       ${server} (reachable)"
      else
        echo "Cluster:       NOT reachable"
      fi
    fi
  fi
}

case "$ACTION" in
  up) up ;;
  down) down ;;
  status) status ;;
  *)
    echo "Usage: $0 [up|down|status] [KUBECONFIG_PATH] [OCP_VERSION]"
    exit 1
    ;;
esac
