#!/bin/bash
# resolve-github-user.sh -- Resolve an Ambient userId to a GitHub username.
#
# Checks .claude/user-map.yaml first (explicit mapping), then falls back to
# fuzzy-matching against the OWNERS file in the repo root.
#
# Usage:
#   bash .claude/scripts/resolve-github-user.sh <userId>
#
# Output: matched GitHub username (stdout), or nothing if no/ambiguous match.

set -euo pipefail

USER_ID="${1:-}"
if [ -z "$USER_ID" ] || [ ${#USER_ID} -lt 3 ]; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- Priority 1: explicit mapping file ---
MAP_FILE="${REPO_ROOT}/.claude/user-map.yaml"
if [ -f "$MAP_FILE" ]; then
  GITHUB_USER=$(python3 -c "
import yaml, sys
with open(sys.argv[1]) as f:
    m = yaml.safe_load(f) or {}
uid = sys.argv[2]
entry = m.get(uid) or m.get(uid.lower())
if isinstance(entry, dict):
    print(entry.get('github', ''), end='')
elif isinstance(entry, str):
    print(entry, end='')
" "$MAP_FILE" "$USER_ID" 2>/dev/null || true)
  if [ -n "$GITHUB_USER" ]; then
    echo "$GITHUB_USER"
    exit 0
  fi
fi

# --- Priority 2: fuzzy match against OWNERS ---
OWNERS_FILE="${REPO_ROOT}/OWNERS"
if [ ! -f "$OWNERS_FILE" ]; then
  exit 0
fi

APPROVERS=$(grep -E '^\s*-\s+' "$OWNERS_FILE" | sed 's/^[[:space:]]*-[[:space:]]*//')
if [ -z "$APPROVERS" ]; then
  exit 0
fi

USER_ID_LOWER=$(echo "$USER_ID" | tr '[:upper:]' '[:lower:]')

match_tier() {
  local tier="$1"
  local matches=()

  while IFS= read -r name; do
    [ -z "$name" ] && continue
    local name_lower
    name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')

    case "$tier" in
      exact)    [ "$name_lower" = "$USER_ID_LOWER" ] && matches+=("$name") ;;
      prefix)   [[ "$name_lower" == "$USER_ID_LOWER"* ]] && matches+=("$name") ;;
      suffix)   [[ "$name_lower" == *"$USER_ID_LOWER" ]] && matches+=("$name") ;;
      contains) [[ "$name_lower" == *"$USER_ID_LOWER"* ]] && matches+=("$name") ;;
    esac
  done <<< "$APPROVERS"

  if [ ${#matches[@]} -eq 1 ]; then
    echo "${matches[0]}"
    return 0
  fi
  return 1
}

match_tier "exact" && exit 0
match_tier "prefix" && exit 0
match_tier "suffix" && exit 0
match_tier "contains" && exit 0
