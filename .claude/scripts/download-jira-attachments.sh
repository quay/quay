#!/bin/bash
# Download attachments from a JIRA issue
# Usage: download-jira-attachments.sh <ISSUE-KEY>

set -e

ISSUE_KEY="$1"

if [ -z "$ISSUE_KEY" ]; then
  echo "Usage: $0 <ISSUE-KEY>"
  exit 1
fi

# Check if jira CLI is installed
if ! command -v jira &> /dev/null; then
  echo "Error: jira CLI is not installed or not in PATH"
  echo "Install from: https://github.com/ankitpokhrel/jira-cli"
  exit 1
fi

# Get raw issue JSON
TEMP_JSON="/tmp/issue-${ISSUE_KEY}.json"
jira issue view "$ISSUE_KEY" --raw > "$TEMP_JSON"

# Check if attachments exist
ATTACHMENT_COUNT=$(jq -r '.fields.attachment | length' "$TEMP_JSON")

if [ "$ATTACHMENT_COUNT" -gt 0 ]; then
  # Create directory for attachments
  ATTACH_DIR=".claude/attachments/${ISSUE_KEY}"
  mkdir -p "$ATTACH_DIR"

  echo "Found $ATTACHMENT_COUNT attachment(s) for $ISSUE_KEY"

  # Get Atlassian Cloud credentials from environment or jira CLI config
  JIRA_CONFIG="${HOME}/.config/.jira/.config.yml"

  if [ -n "$JIRA_API_TOKEN" ] && [ -n "$JIRA_EMAIL" ]; then
    EMAIL="$JIRA_EMAIL"
    TOKEN="$JIRA_API_TOKEN"
  elif [ -f "$JIRA_CONFIG" ]; then
    EMAIL=$(grep 'login:' "$JIRA_CONFIG" | head -1 | awk '{print $2}')
    TOKEN=$(grep 'api_token:' "$JIRA_CONFIG" | head -1 | awk '{print $2}')
  fi

  if [ -z "$EMAIL" ] || [ -z "$TOKEN" ]; then
    echo "Error: Could not determine JIRA credentials."
    echo "Set JIRA_EMAIL and JIRA_API_TOKEN env vars, or configure jira CLI (~/.config/.jira/.config.yml)."
    exit 1
  fi

  # base64 -b 0 on macOS, -w 0 on Linux to avoid line wrapping
  if [[ "$(uname)" == "Darwin" ]]; then
    B64_ENCODED=$(printf '%s:%s' "$EMAIL" "$TOKEN" | base64 -b 0)
  else
    B64_ENCODED=$(printf '%s:%s' "$EMAIL" "$TOKEN" | base64 -w 0)
  fi
  AUTH_HEADER="Authorization: Basic ${B64_ENCODED}"

  # Extract and download each attachment
  jq -r '.fields.attachment[] | "\(.filename)|\(.content)"' "$TEMP_JSON" | while IFS='|' read -r filename url; do
    echo "  Downloading: $filename"

    curl -s -L -H "$AUTH_HEADER" \
      -o "$ATTACH_DIR/$filename" \
      "$url"
  done

  echo "Downloaded to: $ATTACH_DIR/"

  # List downloaded files with their types
  echo ""
  echo "Attachments:"
  for file in "$ATTACH_DIR"/*; do
    if [ -f "$file" ]; then
      basename "$file"
      file -b "$file" | head -c 80
      echo ""
    fi
  done
else
  echo "No attachments found for $ISSUE_KEY"
fi

# Clean up temp file
rm -f "$TEMP_JSON"
