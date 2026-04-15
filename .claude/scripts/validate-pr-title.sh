#!/bin/bash
# validate-pr-title.sh -- Validate PR title matches the required format.
#
# Usage: bash scripts/validate-pr-title.sh "PROJQUAY-1234: fix(api): add pagination"
#
# The PR title must match (enforced by CI pull_request_linting.yaml):
#   ^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$
#
# Valid examples:
#   PROJQUAY-1234: fix(api): add pagination to tag listing
#   PROJQUAY-5678: feat(web): add mirror config page
#   QUAYIO-9999: chore: update dependencies
#   NO-ISSUE: docs: update README
#   [redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination

set -euo pipefail

TITLE="${1:?Usage: validate-pr-title.sh \"<PR TITLE>\"}"

# The regex from .github/workflows/pull_request_linting.yaml
PATTERN='^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(\([^)]+\))?: .+$'

if echo "$TITLE" | grep -qP "$PATTERN" 2>/dev/null || echo "$TITLE" | grep -qE "$PATTERN" 2>/dev/null; then
  echo "VALID: \"${TITLE}\""
  echo ""
  echo "Format breakdown:"

  # Extract parts
  BACKPORT_PREFIX=$(echo "$TITLE" | grep -oP '^\[redhat-[0-9]+\.[0-9]+\] ' 2>/dev/null || true)
  JIRA_REF=$(echo "$TITLE" | grep -oP '(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE)' 2>/dev/null || echo "?")
  TYPE=$(echo "$TITLE" | sed -E 's/^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): ([a-z]+).*/\3/' 2>/dev/null || echo "?")
  SCOPE=$(echo "$TITLE" | grep -oP '(?<=\()[^)]+(?=\))' 2>/dev/null || echo "(none)")

  [ -n "$BACKPORT_PREFIX" ] && echo "  Backport:  ${BACKPORT_PREFIX}"
  echo "  JIRA ref:  ${JIRA_REF}"
  echo "  Type:      ${TYPE}"
  echo "  Scope:     ${SCOPE}"
  exit 0
else
  echo "INVALID: \"${TITLE}\""
  echo ""
  echo "Required format:"
  echo "  [optional backport prefix] JIRA-REF: type(optional-scope): description"
  echo ""
  echo "Valid types: fix, feat, chore, docs, test, refactor, perf, style, ci, build, deps"
  echo ""
  echo "Examples:"
  echo "  PROJQUAY-1234: fix(api): add pagination to tag listing"
  echo "  PROJQUAY-5678: feat(web): add mirror config page"
  echo "  NO-ISSUE: chore: update dependencies"
  echo "  [redhat-3.12] PROJQUAY-1234: fix(api): backport tag pagination"
  exit 1
fi
