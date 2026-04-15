#!/bin/bash
# jira-ops.sh -- JIRA operations for the Quay development workflow.
#
# Usage:
#   bash scripts/jira-ops.sh view <ISSUE_KEY>
#   bash scripts/jira-ops.sh assign <ISSUE_KEY> [assignee]
#   bash scripts/jira-ops.sh transition <ISSUE_KEY> <status>
#   bash scripts/jira-ops.sh check-version <ISSUE_KEY>
#   bash scripts/jira-ops.sh set-version <ISSUE_KEY> <version>
#
# Requires: gh CLI (for REST API calls to JIRA) OR acli
# Falls back to REST API if acli is unavailable.

set -euo pipefail

ACTION="${1:?Usage: jira-ops.sh <action> <ISSUE_KEY> [args...]}"
ISSUE_KEY="${2:?Usage: jira-ops.sh <action> <ISSUE_KEY> [args...]}"
shift 2

# "Target Version" custom field ID (multi-version picker)
TV_FIELD="customfield_10855"

# ── Detect JIRA CLI tool ──────────────────────────────────────────
JIRA_CLI=""
if command -v acli &>/dev/null; then
  JIRA_CLI="acli"
fi

# ── Helper: extract JIRA credentials for REST API ─────────────────
get_jira_creds() {
  local email="" token=""

  if [ -f "$HOME/.config/acli/jira_config.yaml" ]; then
    email=$(grep -E '^\s*email:' "$HOME/.config/acli/jira_config.yaml" | awk '{print $2}' | head -1)
  fi

  for f in "$HOME/.config/acli/token.txt" "$HOME/.acli-token"; do
    if [ -f "$f" ]; then
      token=$(cat "$f")
      break
    fi
  done

  [ -z "$token" ] && token="${JIRA_API_TOKEN:-}"
  [ -z "$email" ] && email="${JIRA_USER:-quay-devel@redhat.com}"

  echo "${email}:${token}"
}

jira_rest() {
  local method="$1" path="$2" data="${3:-}"
  local creds
  creds=$(get_jira_creds)

  if [ -z "$creds" ] || [ "$creds" = ":" ]; then
    echo "ERROR: No JIRA credentials found. Set up acli or JIRA_USER/JIRA_API_TOKEN env vars." >&2
    return 1
  fi

  local args=(-sS -f -H "Content-Type: application/json" -u "$creds")
  if [ -n "$data" ]; then
    args+=(-X "$method" -d "$data")
  fi

  curl "${args[@]}" "https://redhat.atlassian.net/rest/api/3/${path}"
}

# ── Helper: extract Target Version from issue JSON ────────────────
extract_target_version() {
  local json="$1"
  # customfield_10855 is a multi-version picker (array of version objects)
  echo "$json" | jq -r "
    .fields.${TV_FIELD} // null |
    if type == \"array\" and length > 0 then
      [.[].name] | join(\", \")
    else
      null
    end
  " 2>/dev/null
}

# ── Actions ───────────────────────────────────────────────────────

case "$ACTION" in
  view)
    echo "Fetching ${ISSUE_KEY}..."
    if [ "$JIRA_CLI" = "acli" ]; then
      acli jira workitem view "$ISSUE_KEY" 2>/dev/null || {
        echo "acli failed, trying REST API..."
        RESULT=$(jira_rest GET "issue/${ISSUE_KEY}")
        TV_VALUE=$(extract_target_version "$RESULT")
        echo "$RESULT" | jq --arg tv "${TV_VALUE:-not set}" '{
          key: .key,
          summary: .fields.summary,
          status: .fields.status.name,
          assignee: (.fields.assignee.displayName // "unassigned"),
          type: .fields.issuetype.name,
          priority: .fields.priority.name,
          target_version: $tv,
          labels: .fields.labels,
          description: ([.fields.description // {} | .. | .text? // empty] | .[0:10] | join(" "))
        }' 2>/dev/null || echo "$RESULT"
      }
    else
      RESULT=$(jira_rest GET "issue/${ISSUE_KEY}")
      TV_VALUE=$(extract_target_version "$RESULT")
      echo "$RESULT" | jq --arg tv "${TV_VALUE:-not set}" '{
        key: .key,
        summary: .fields.summary,
        status: .fields.status.name,
        assignee: (.fields.assignee.displayName // "unassigned"),
        type: .fields.issuetype.name,
        priority: .fields.priority.name,
        target_version: $tv,
        labels: .fields.labels,
        description: ([.fields.description // {} | .. | .text? // empty] | .[0:10] | join(" "))
      }' 2>/dev/null || echo "$RESULT"
    fi
    ;;

  assign)
    ASSIGNEE="${1:-}"
    echo "Assigning ${ISSUE_KEY}..."
    if [ "$JIRA_CLI" = "acli" ]; then
      if [ -n "$ASSIGNEE" ]; then
        acli jira workitem edit --key "$ISSUE_KEY" --assignee "$ASSIGNEE" --yes
      else
        acli jira workitem edit --key "$ISSUE_KEY" --assignee "@me" --yes
      fi
    else
      if [ -n "$ASSIGNEE" ]; then
        DATA=$(jq -n --arg id "$ASSIGNEE" '{"fields":{"assignee":{"accountId":$id}}}')
        jira_rest PUT "issue/${ISSUE_KEY}" "$DATA"
      else
        echo "Cannot auto-assign via REST without knowing your username. Use acli or pass username."
        exit 1
      fi
    fi
    echo "Assigned."
    ;;

  transition)
    STATUS="${1:?Usage: jira-ops.sh transition <ISSUE_KEY> <status>}"
    echo "Transitioning ${ISSUE_KEY} to '${STATUS}'..."
    if [ "$JIRA_CLI" = "acli" ]; then
      acli jira workitem transition --key "$ISSUE_KEY" --status "$STATUS" --yes 2>/dev/null || {
        echo "Transition failed. Available transitions:"
        acli jira workitem transitions --key "$ISSUE_KEY" 2>/dev/null || echo "(could not list transitions)"
      }
    else
      TRANSITIONS=$(jira_rest GET "issue/${ISSUE_KEY}/transitions")
      TRANSITION_ID=$(echo "$TRANSITIONS" | jq -r ".transitions[] | select(.name | ascii_downcase == (\"${STATUS}\" | ascii_downcase)) | .id" | head -1)
      if [ -n "$TRANSITION_ID" ]; then
        jira_rest POST "issue/${ISSUE_KEY}/transitions" "{\"transition\":{\"id\":\"${TRANSITION_ID}\"}}"
        echo "Transitioned to '${STATUS}'."
      else
        echo "Transition '${STATUS}' not available. Available:"
        echo "$TRANSITIONS" | jq -r '.transitions[].name' 2>/dev/null
      fi
    fi
    ;;

  check-version)
    echo "Checking Target Version for ${ISSUE_KEY}..."
    RESULT=$(jira_rest GET "issue/${ISSUE_KEY}?fields=${TV_FIELD}")
    TV_VALUE=$(extract_target_version "$RESULT")

    if [ -n "$TV_VALUE" ] && [ "$TV_VALUE" != "null" ]; then
      echo "Target Version: ${TV_VALUE}"
      echo "Backporting REQUIRED after merge."
    else
      echo "No Target Version set. Backporting not required."
    fi
    ;;

  set-version)
    VERSION="${1:?Usage: jira-ops.sh set-version <ISSUE_KEY> <version>}"
    echo "Setting Target Version on ${ISSUE_KEY} to '${VERSION}'..."
    DATA=$(jq -n --arg ver "$VERSION" --arg field "$TV_FIELD" '{fields: {($field): [{"name": $ver}]}}')
    jira_rest PUT "issue/${ISSUE_KEY}" "$DATA"
    echo "Target Version set to '${VERSION}'."
    ;;

  *)
    echo "Unknown action: ${ACTION}"
    echo "Usage: jira-ops.sh <view|assign|transition|check-version|set-version> <ISSUE_KEY> [args...]"
    exit 1
    ;;
esac
