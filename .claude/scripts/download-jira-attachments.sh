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

  # Get bearer token from environment or jira config
  if [ -n "$JIRA_API_TOKEN" ]; then
    JIRA_TOKEN="$JIRA_API_TOKEN"
  else
    JIRA_TOKEN=$(grep -A2 'auth_type: bearer' ~/.config/.jira/.config.yml | grep -v 'auth_type' | grep -v '^--$' | awk '{print $2}')
  fi

  if [ -z "$JIRA_TOKEN" ]; then
    echo "Error: Could not find JIRA bearer token. Set JIRA_API_TOKEN env var or configure in ~/.config/.jira/.config.yml"
    exit 1
  fi

  # Extract and download each attachment
  jq -r '.fields.attachment[] | "\(.filename)|\(.content)"' "$TEMP_JSON" | while IFS='|' read -r filename url; do
    echo "  Downloading: $filename"

    curl -s -H "Authorization: Bearer $JIRA_TOKEN" \
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
