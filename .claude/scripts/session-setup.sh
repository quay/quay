#!/bin/bash
# session-setup.sh -- One-time session bootstrap for Quay development.
#
# Handles: acli install+auth, recommended hooks, pre-commit, gh auth check.
# Called by /start skill as Step 0, or run manually.
#
# Usage:
#   bash .claude/scripts/session-setup.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SETUP_MARKER="${HOME}/.quay-session-setup-done"

# Skip if already run this session
if [ -f "$SETUP_MARKER" ]; then
  echo "Session already bootstrapped. Delete ${SETUP_MARKER} to re-run."
  exit 0
fi

echo "=== Quay Session Bootstrap ==="

# ── 1. acli ──────────────────────────────────────────────────────
if ! command -v acli &>/dev/null; then
  echo "[1/4] Installing acli..."
  install_dir="${HOME}/.local/bin"
  mkdir -p "$install_dir"
  curl -sSL -o "${install_dir}/acli" "https://acli.atlassian.com/linux/latest/acli_linux_amd64/acli"
  chmod +x "${install_dir}/acli"
  export PATH="${install_dir}:${PATH}"
  echo "  Installed to ${install_dir}/acli"
else
  echo "[1/4] acli already installed."
fi

# Auth acli if credentials available
if command -v acli &>/dev/null; then
  if ! acli jira auth status &>/dev/null; then
    token="${JIRA_API_TOKEN:-}"
    email="${JIRA_USER:-quay-devel@redhat.com}"
    if [ -n "$token" ]; then
      echo "$token" | acli jira auth login         --site "redhat.atlassian.net"         --email "$email" --token 2>/dev/null && echo "  acli authenticated as ${email}." ||         echo "  Warning: acli auth failed. Run manually: acli jira auth login --site redhat.atlassian.net --email ${email} --token"
    else
      echo "  Warning: No JIRA_API_TOKEN set. Set it or run: acli jira auth login --site redhat.atlassian.net --email <email> --token"
    fi
  else
    echo "  acli already authenticated."
  fi
fi

# ── 2. Recommended hooks ────────────────────────────────────────
echo "[2/4] Checking Claude Code hooks..."
settings_src="${REPO_ROOT}/.claude/claude-settings-recommended.json"
settings_dst="${REPO_ROOT}/.claude/settings.json"
if [ -f "$settings_src" ]; then
  if [ ! -f "$settings_dst" ]; then
    cp "$settings_src" "$settings_dst"
    echo "  Installed recommended hooks."
  else
    echo "  settings.json exists. Merge hooks manually if needed."
  fi
else
  echo "  No recommended settings found at ${settings_src}."
fi

# ── 3. pre-commit ───────────────────────────────────────────────
echo "[3/4] Checking pre-commit hooks..."
if [ -f "${REPO_ROOT}/.pre-commit-config.yaml" ]; then
  if command -v pre-commit &>/dev/null; then
    (cd "$REPO_ROOT" && pre-commit install --allow-missing-config 2>/dev/null) && echo "  pre-commit hooks installed." || echo "  pre-commit install failed (non-fatal)."
  else
    echo "  pre-commit not found (hooks will run in CI)."
  fi
else
  echo "  No .pre-commit-config.yaml found."
fi

# ── 4. gh CLI ───────────────────────────────────────────────────
echo "[4/4] Checking GitHub CLI auth..."
if command -v gh &>/dev/null; then
  if gh auth status &>/dev/null; then
    echo "  gh authenticated."
  else
    echo "  Warning: gh not authenticated. Run: gh auth login"
  fi
else
  echo "  Warning: gh CLI not found."
fi

# Mark complete
touch "$SETUP_MARKER"
echo "=== Bootstrap complete ==="
