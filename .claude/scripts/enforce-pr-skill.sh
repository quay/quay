#!/bin/bash
# enforce-pr-skill.sh -- PreToolUse hook for gh pr create.
# Ensures the /pr skill conventions are followed before creating a PR:
#   1. /tmp/pr-body.md exists with required template sections
#   2. The command references /tmp/pr-body.md for the body
#   3. If AGENTIC_SESSION_NAME is set, --label "ambient-session" is present
#   4. --base flag is specified

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

ERRORS=()

# --- Check 1: /tmp/pr-body.md exists and has required template sections ---
if [ ! -f /tmp/pr-body.md ]; then
  ERRORS+=("PR body file /tmp/pr-body.md not found. The /pr skill writes the filled PR description template there before creating the PR. Run /pr to create PRs correctly.")
else
  REQUIRED_SECTIONS=("## Summary" "## Test Plan" "## JIRA")
  for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -qF "$section" /tmp/pr-body.md; then
      ERRORS+=("PR body file /tmp/pr-body.md is missing required section: $section. Use the template at .claude/templates/pr-description.md.")
    fi
  done
fi

# --- Check 2: Command references /tmp/pr-body.md for the body ---
if ! echo "$CMD" | grep -q 'pr-body\.md'; then
  ERRORS+=("The gh pr create command must use /tmp/pr-body.md for the --body content (e.g., --body \"\$(cat /tmp/pr-body.md)\"). The /pr skill prepares the body there from the description template.")
fi

# --- Check 3: Ambient session label ---
if [ -n "${AGENTIC_SESSION_NAME:-}" ]; then
  if ! echo "$CMD" | grep -q -- '--label.*ambient-session\|ambient-session.*--label'; then
    ERRORS+=("AGENTIC_SESSION_NAME is set ($AGENTIC_SESSION_NAME) but --label \"ambient-session\" is missing. The /pr skill requires this label for ambient session PRs.")
  fi
fi

# --- Check 4: --base flag is specified ---
if ! echo "$CMD" | grep -q -- '--base'; then
  ERRORS+=("Missing --base flag. The /pr skill requires --base master (or the target branch for backports).")
fi

# --- Report ---
if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "BLOCKED: gh pr create does not follow /pr skill conventions." >&2
  echo "" >&2
  for err in "${ERRORS[@]}"; do
    echo "  - $err" >&2
  done
  echo "" >&2
  echo "Use the /pr skill to create PRs correctly, or fix the issues above." >&2
  exit 2
fi
