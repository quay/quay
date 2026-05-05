#!/bin/bash
# resolve-github-user.sh -- Resolve an Ambient userId to a GitHub username
# by fuzzy-matching against the OWNERS file in the repo root.
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
match_tier "suffix" && exit 0
match_tier "contains" && exit 0
