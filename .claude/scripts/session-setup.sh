#!/bin/bash
# session-setup.sh -- One-time session bootstrap for Quay development.
#
# Handles: acli install+auth, pre-commit, gh auth check.
# Runs automatically via SessionStart hook, or manually.
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
  echo "[1/3] Installing acli..."
  install_dir="${HOME}/.local/bin"
  mkdir -p "$install_dir"
  curl -sSL -o "${install_dir}/acli" "https://acli.atlassian.com/linux/latest/acli_linux_amd64/acli"
  chmod +x "${install_dir}/acli"
  export PATH="${install_dir}:${PATH}"
  echo "  Installed to ${install_dir}/acli"
else
  echo "[1/3] acli already installed."
fi

# Auth acli if credentials available
if command -v acli &>/dev/null; then
  if ! acli jira auth status &>/dev/null; then
    token="${JIRA_API_TOKEN:-}"
    email="${JIRA_USER:-quay-devel@redhat.com}"
    if [ -n "$token" ]; then
      echo "$token" | acli jira auth login \
        --site "redhat.atlassian.net" \
        --email "$email" --token 2>/dev/null && echo "  acli authenticated as ${email}." || \
        echo "  Warning: acli auth failed. Run manually: acli jira auth login --site redhat.atlassian.net --email ${email} --token"
    else
      echo "  Warning: No JIRA_API_TOKEN set. Set it or run: acli jira auth login --site redhat.atlassian.net --email <email> --token"
    fi
  else
    echo "  acli already authenticated."
  fi
fi

# ── 2. pre-commit ───────────────────────────────────────────────
echo "[2/3] Checking pre-commit hooks..."
if [ -f "${REPO_ROOT}/.pre-commit-config.yaml" ]; then
  if command -v pre-commit &>/dev/null; then
    (cd "$REPO_ROOT" && pre-commit install --allow-missing-config 2>/dev/null) && echo "  pre-commit hooks installed." || echo "  pre-commit install failed (non-fatal)."
  else
    echo "  pre-commit not found (hooks will run in CI)."
  fi
else
  echo "  No .pre-commit-config.yaml found."
fi

# ── 3. gh CLI ───────────────────────────────────────────────────
echo "[3/3] Checking GitHub CLI auth..."
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
