#!/usr/bin/env bash
set -euo pipefail

# Deploy a Playwright browser server pod to an OpenShift/K8s cluster.
# Resolves @playwright/cli's dependency version automatically so the
# server always matches the client.
#
# Usage: remote-playwright.sh [up|down|status] [KUBECONFIG_PATH] [NAMESPACE]

ACTION="${1:-up}"
KUBECONFIG_PATH="${2:-/tmp/k}"
NAMESPACE="${3:-playwright}"

export KUBECONFIG="$KUBECONFIG_PATH"

PF_DIR=/tmp/pw-remote
PF_PID_FILE="$PF_DIR/port-forward.pid"
MANAGED_BY_LABEL="app.kubernetes.io/managed-by=remote-playwright"

stop_port_forward() {
  if [[ -f "$PF_PID_FILE" ]]; then
    local pid
    pid="$(cat "$PF_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$PF_PID_FILE"
  fi
}

pf_is_active() {
  [[ -f "$PF_PID_FILE" ]] && kill -0 "$(cat "$PF_PID_FILE" 2>/dev/null)" 2>/dev/null
}

status() {
  echo "=== Remote Playwright Status ==="
  echo "Kubeconfig: $KUBECONFIG_PATH"
  echo "Namespace:  $NAMESPACE"
  oc get pods -n "$NAMESPACE" -l app=playwright-server 2>/dev/null || echo "No pods found"
  echo ""
  if pf_is_active; then
    echo "Port-forward: active (pid $(cat "$PF_PID_FILE"))"
  else
    echo "Port-forward: inactive"
  fi
}

down() {
  echo "Tearing down remote playwright..."
  stop_port_forward
  oc delete deployment/playwright-server service/playwright-server \
    -n "$NAMESPACE" --ignore-not-found 2>/dev/null || true
  if oc get namespace "$NAMESPACE" -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}' 2>/dev/null \
      | grep -qx 'remote-playwright'; then
    oc delete namespace "$NAMESPACE" --ignore-not-found 2>/dev/null || true
  fi
  echo "Done."
}

connect() {
  mkdir -p "$PF_DIR"

  if ! pf_is_active; then
    echo "Setting up port-forward..."
    stop_port_forward
    oc port-forward -n "$NAMESPACE" svc/playwright-server 3000:3000 > /tmp/pf-playwright.log 2>&1 &
    echo $! > "$PF_PID_FILE"
    sleep 3
    if ! pf_is_active; then
      echo "ERROR: Port-forward failed" >&2
      cat /tmp/pf-playwright.log
      rm -f "$PF_PID_FILE"
      exit 1
    fi
  fi
  echo "Port-forward active (pid $(cat "$PF_PID_FILE"))"

  cat > "$PF_DIR/cli.config.json" << 'CLIEOF'
{
  "browser": {
    "remoteEndpoint": "ws://localhost:3000/",
    "isolated": true
  }
}
CLIEOF

  echo "Connecting @playwright/cli..."
  npx @playwright/cli attach --config "$PF_DIR/cli.config.json" 2>&1

  echo ""
  echo "=== Ready ==="
  echo "Commands:"
  echo "  npx @playwright/cli goto <url>"
  echo "  npx @playwright/cli snapshot"
  echo "  npx @playwright/cli screenshot"
  echo "  npx @playwright/cli click <ref>"
  echo "  npx @playwright/cli fill <ref> <text>"
  echo "  npx @playwright/cli video-start / video-stop"
}

pick_docker_tag() {
  local prefix="$1"
  curl -sL "https://mcr.microsoft.com/v2/playwright/tags/list" 2>/dev/null \
    | python3 -c "
import sys, json
tags = json.load(sys.stdin).get('tags', [])
candidates = [t for t in tags if t.startswith('${prefix}') and t.endswith('-noble') and 'alpha' not in t and 'beta' not in t]
def version_key(tag):
    base = tag.split('-', 1)[0].lstrip('v')
    return tuple(int(part) for part in base.split('.'))
if candidates:
    print(max(candidates, key=version_key))
" 2>/dev/null || true
}

up() {
  echo "Resolving @playwright/cli dependency version..."
  PW_VERSION=$(npm info @playwright/cli@latest dependencies.playwright 2>/dev/null)
  if [[ -z "$PW_VERSION" ]]; then
    echo "ERROR: Could not resolve playwright version from @playwright/cli" >&2
    exit 1
  fi
  echo "Playwright version: $PW_VERSION"

  PW_MAJOR_MINOR=$(echo "$PW_VERSION" | grep -oP '^\d+\.\d+')
  DOCKER_TAG=$(pick_docker_tag "v${PW_MAJOR_MINOR}.")

  # Fallback: try prior minor version if no stable image for this series
  if [[ -z "$DOCKER_TAG" ]]; then
    PREV_MINOR=$((${PW_MAJOR_MINOR##*.} - 1))
    PW_MAJOR="${PW_MAJOR_MINOR%%.*}"
    DOCKER_TAG=$(pick_docker_tag "v${PW_MAJOR}.${PREV_MINOR}.")
  fi

  if [[ -z "$DOCKER_TAG" ]]; then
    echo "ERROR: Could not find a suitable Playwright Docker image" >&2
    exit 1
  fi
  echo "Docker image:  mcr.microsoft.com/playwright:$DOCKER_TAG"

  echo "Checking cluster..."
  oc whoami --show-server

  # Check if already running with matching image
  if oc get pods -n "$NAMESPACE" -l app=playwright-server --field-selector=status.phase=Running 2>/dev/null | grep -q Running; then
    RUNNING_IMAGE=$(oc get deployment/playwright-server -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)
    if [[ "$RUNNING_IMAGE" == "mcr.microsoft.com/playwright:$DOCKER_TAG" ]]; then
      echo "Playwright server already running in $NAMESPACE (image matches)"
      stop_port_forward
      sleep 1
      connect
      return 0
    fi
    echo "Running server image ($RUNNING_IMAGE) differs from resolved (mcr.microsoft.com/playwright:$DOCKER_TAG) — redeploying..."
  fi

  echo "Deploying playwright server..."
  oc apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    app.kubernetes.io/managed-by: remote-playwright
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: playwright-server
  namespace: $NAMESPACE
  labels:
    app: playwright-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: playwright-server
  template:
    metadata:
      labels:
        app: playwright-server
    spec:
      containers:
        - name: playwright
          image: mcr.microsoft.com/playwright:$DOCKER_TAG
          command:
            - /bin/sh
            - -c
            - |
              npx playwright@$PW_VERSION install chromium &&
              xvfb-run npx playwright@$PW_VERSION run-server --host 0.0.0.0 --port 3000 --mode extension
          env:
            - name: HOME
              value: /tmp
            - name: npm_config_cache
              value: /tmp/.npm
          ports:
            - containerPort: 3000
              protocol: TCP
          volumeMounts:
            - name: dshm
              mountPath: /dev/shm
          resources:
            requests:
              cpu: "1"
              memory: 2Gi
            limits:
              cpu: "2"
              memory: 4Gi
      volumes:
        - name: dshm
          emptyDir:
            medium: Memory
            sizeLimit: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: playwright-server
  namespace: $NAMESPACE
spec:
  selector:
    app: playwright-server
  ports:
    - port: 3000
      targetPort: 3000
      protocol: TCP
EOF

  echo "Waiting for rollout..."
  oc rollout status deployment/playwright-server -n "$NAMESPACE" --timeout=300s

  local ready=false
  for _i in $(seq 1 30); do
    if oc logs -n "$NAMESPACE" deployment/playwright-server --tail=5 2>/dev/null | grep -q "Listening on"; then
      echo "Server is listening."
      ready=true
      break
    fi
    sleep 2
  done

  if [[ "$ready" != "true" ]]; then
    echo "ERROR: Server failed to start within 60s" >&2
    oc logs -n "$NAMESPACE" deployment/playwright-server --tail=30 2>/dev/null || true
    exit 1
  fi

  connect
}

case "$ACTION" in
  up)     up ;;
  down)   down ;;
  status) status ;;
  *)      echo "Usage: $0 [up|down|status] [KUBECONFIG] [NAMESPACE]"; exit 1 ;;
esac
