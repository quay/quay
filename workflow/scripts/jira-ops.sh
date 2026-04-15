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
# Falls back to gh-based JIRA interaction if acli is unavailable.
#
# Note: "Target Version" is a JIRA custom field (not the built-in fixVersions).
# The script discovers the custom field ID dynamically by searching for a field
# named "Target Version". Set TARGET_VERSION_FIELD_ID to override (e.g., customfield_12345).

set -euo pipefail

ACTION="${1:?Usage: jira-ops.sh <action> <ISSUE_KEY> [args...]}"
ISSUE_KEY="${2:?Usage: jira-ops.sh <action> <ISSUE_KEY> [args...]}"
shift 2

# ── Detect JIRA CLI tool ──────────────────────────────────────────
JIRA_CLI=""
if command -v acli &>/dev/null; then
  JIRA_CLI="acli"
fi

# ── Helper: extract JIRA credentials for REST API ─────────────────
get_jira_creds() {
  local email="" token=""

  # Try acli config
  if [ -f "$HOME/.config/acli/jira_config.yaml" ]; then
    email=$(grep -E '^\s*email:' "$HOME/.config/acli/jira_config.yaml" | awk '{print $2}' | head -1)
  fi

  # Try token files
  for f in "$HOME/.config/acli/token.txt" "$HOME/.acli-token"; do
    if [ -f "$f" ]; then
      token=$(cat "$f")
      break
    fi
  done

  # Fallback to env var
  [ -z "$token" ] && token="${JIRA_API_TOKEN:-}"
  [ -z "$email" ] && email="${JIRA_USER:-}"

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

  local args=(-s -H "Content-Type: application/json" -u "$creds")
  if [ -n "$data" ]; then
    args+=(-X "$method" -d "$data")
  fi

  curl "${args[@]}" "https://issues.redhat.com/rest/api/2/${path}"
}

# ── Helper: resolve "Target Version" custom field ID ──────────────
# Caches the result in a temp file to avoid repeated API calls.
get_target_version_field_id() {
  # Allow override via env var
  if [ -n "${TARGET_VERSION_FIELD_ID:-}" ]; then
    echo "$TARGET_VERSION_FIELD_ID"
    return
  fi

  local cache_file="/tmp/.jira-target-version-field-id"
  if [ -f "$cache_file" ] && [ "$(find "$cache_file" -mmin -60 2>/dev/null)" ]; then
    cat "$cache_file"
    return
  fi

  local field_id
  field_id=$(jira_rest GET "field" | \
    jq -r '.[] | select(.name == "Target Version") | .id' 2>/dev/null | head -1)

  if [ -n "$field_id" ]; then
    echo "$field_id" > "$cache_file"
    echo "$field_id"
  else
    echo "ERROR: Could not find 'Target Version' custom field. Set TARGET_VERSION_FIELD_ID env var." >&2
    return 1
  fi
}

# ── Helper: extract Target Version value from issue JSON ──────────
extract_target_version() {
  local json="$1" field_id="$2"

  # Target Version can be a string, object with .name, or array of objects
  echo "$json" | jq -r "
    .fields[\"${field_id}\"] //
    null |
    if type == \"array\" then
      if length > 0 then [.[].name // .[].value // .[] | tostring] | join(\", \") else null end
    elif type == \"object\" then
      .name // .value // tostring
    elif type == \"string\" then
      .
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
        TV_FIELD=$(get_target_version_field_id 2>/dev/null || echo "")
        RESULT=$(jira_rest GET "issue/${ISSUE_KEY}")
        TV_VALUE=""
        if [ -n "$TV_FIELD" ]; then
          TV_VALUE=$(extract_target_version "$RESULT" "$TV_FIELD")
        fi
        echo "$RESULT" | jq --arg tv "${TV_VALUE:-not set}" '{
          key: .key,
          summary: .fields.summary,
          status: .fields.status.name,
          assignee: .fields.assignee.displayName,
          type: .fields.issuetype.name,
          priority: .fields.priority.name,
          target_version: $tv,
          labels: .fields.labels,
          description: (.fields.description | split("\n") | .[0:10] | join("\n"))
        }' 2>/dev/null || echo "$RESULT"
      }
    else
      TV_FIELD=$(get_target_version_field_id 2>/dev/null || echo "")
      RESULT=$(jira_rest GET "issue/${ISSUE_KEY}")
      TV_VALUE=""
      if [ -n "$TV_FIELD" ]; then
        TV_VALUE=$(extract_target_version "$RESULT" "$TV_FIELD")
      fi
      echo "$RESULT" | jq --arg tv "${TV_VALUE:-not set}" '{
        key: .key,
        summary: .fields.summary,
        status: .fields.status.name,
        assignee: .fields.assignee.displayName,
        type: .fields.issuetype.name,
        priority: .fields.priority.name,
        target_version: $tv,
        labels: .fields.labels,
        description: (.fields.description | split("\n") | .[0:10] | join("\n"))
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
        jira_rest PUT "issue/${ISSUE_KEY}" "{\"fields\":{\"assignee\":{\"name\":\"${ASSIGNEE}\"}}}"
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
      # Get available transitions
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
    TV_FIELD=$(get_target_version_field_id) || exit 1
    RESULT=$(jira_rest GET "issue/${ISSUE_KEY}?fields=${TV_FIELD}")
    TV_VALUE=$(extract_target_version "$RESULT" "$TV_FIELD")

    if [ -n "$TV_VALUE" ] && [ "$TV_VALUE" != "null" ]; then
      echo "Target Version: ${TV_VALUE}"
      echo "Backporting REQUIRED after merge."
    else
      echo "No Target Version set. Backporting not required."
    fi
    ;;

  set-version)
    VERSION="${1:?Usage: jira-ops.sh set-version <ISSUE_KEY> <version>}"
    TV_FIELD=$(get_target_version_field_id) || exit 1
    echo "Setting Target Version on ${ISSUE_KEY} to '${VERSION}'..."
    # Try as object with name (version picker), fall back to string value
    jira_rest PUT "issue/${ISSUE_KEY}" "{\"fields\":{\"${TV_FIELD}\":{\"name\":\"${VERSION}\"}}}" 2>/dev/null || \
    jira_rest PUT "issue/${ISSUE_KEY}" "{\"fields\":{\"${TV_FIELD}\":\"${VERSION}\"}}"
    echo "Target Version set to '${VERSION}'."
    ;;

  *)
    echo "Unknown action: ${ACTION}"
    echo "Usage: jira-ops.sh <view|assign|transition|check-version|set-version> <ISSUE_KEY> [args...]"
    exit 1
    ;;
esac
