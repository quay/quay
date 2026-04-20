---
name: remote-playwright
description: >
  Deploy and connect to a remote Playwright browser on an OpenShift cluster.
  Sets up a Playwright run-server pod, port-forwarding, and @playwright/cli
  for interactive browser automation (goto, click, snapshot, screenshot,
  video recording). Use when you need a remote browser for E2E interaction
  or visual verification on a cluster.
argument-hint: "[KUBECONFIG_PATH] [NAMESPACE]"
allowed-tools:
  - Bash(bash .claude/scripts/remote-playwright.sh *)
  - Bash(npx @playwright/cli*)
  - Read
---

# Remote Playwright Browser

Deploy and connect to a Playwright browser running on an OpenShift cluster.

## Arguments

Parse `$ARGUMENTS` into at most two values before invoking Bash:
- **Arg 1**: KUBECONFIG path (default: `/tmp/k`)
- **Arg 2**: Namespace (default: `playwright`)

Set variables from `$ARGUMENTS`:
```
KUBECONFIG_PATH = first arg or /tmp/k
NAMESPACE = second arg or playwright
```

## Step 1: Deploy and Connect

```bash
bash .claude/scripts/remote-playwright.sh up "$KUBECONFIG_PATH" "$NAMESPACE"
```

The script handles everything: version resolution, deployment, port-forwarding, and CLI connection. Wait for the `=== Ready ===` output.

## Step 2: Verify

```bash
npx @playwright/cli goto https://example.com
npx @playwright/cli snapshot
npx @playwright/cli screenshot
```

## Step 3: Report

Summarize connection status and remind user of available commands:
- `npx @playwright/cli goto <url>` -- navigate
- `npx @playwright/cli snapshot` -- accessibility tree
- `npx @playwright/cli screenshot` -- save PNG
- `npx @playwright/cli click <ref>` -- click element by ref from snapshot
- `npx @playwright/cli fill <ref> <text>` -- fill input
- `npx @playwright/cli video-start` / `video-stop` -- record session
- `npx @playwright/cli tab-list` / `tab-new` / `tab-select` -- manage tabs
- `npx @playwright/cli cookie-list` / `state-save` / `state-load` -- session state

## Teardown

```bash
bash .claude/scripts/remote-playwright.sh down "$KUBECONFIG_PATH" "$NAMESPACE"
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `428 Precondition Required` | Version mismatch -- re-run `up` to auto-resolve |
| `unable to connect to a browser that does not have any contexts` | Config missing `isolated: true` -- re-run `up` |
| Port 3000 in use | Re-run `up` -- it kills stale forwards automatically |
