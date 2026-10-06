#!/usr/bin/env bash
set -euo pipefail

# Pin the locale so bracket ranges like [a-z] and [0-9] match only ASCII,
# matching the old JS regex's behavior regardless of the runner's locale.
export LC_ALL=C

if [ -n "${PR_TITLE:-}" ]; then
  title="$PR_TITLE"
else
  title="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" --jq .title)"
fi

full_regex='^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(\([^)]+\))?: .+$'
prefix_regex='^(\[redhat-[0-9]+\.[0-9]+\] )?(PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): '
type_regex='^[a-z]+(\([^)]+\))?: '

if [[ "$title" =~ $full_regex ]]; then
  echo "PR title OK: $title"
  exit 0
fi

echo "::error::PR title check failed (commit messages are not checked; the squash-merge commit uses the PR title)."
echo "Title: $title"

if [[ "$title" =~ $prefix_regex ]]; then
  prefix="${BASH_REMATCH[0]}"
  rest="${title#"$prefix"}"
  if ! [[ "$rest" =~ $type_regex ]]; then
    echo 'Missing part: the prefix is present but there is no conventional "<type>(<scope>): " after it.'
  else
    echo "Missing part: the title does not match the expected shape."
  fi
else
  echo 'Missing part: no ticket prefix "PROJQUAY-<n>: ", "QUAYIO-<n>: ", or "NO-ISSUE: " (backport form "[redhat-X.Y] " goes before it).'
fi

echo ""
echo 'Expected shape: "<TICKET>: <type>(<scope>): <description>", where <type> is lowercase letters and "(<scope>)" is optional.'
echo "Examples:"
echo "  PROJQUAY-1234: fix(api): handle empty manifest list"
echo "  NO-ISSUE: docs(security): clarify the disclosure policy"
echo "  [redhat-3.17] PROJQUAY-1234: fix(ui): correct tag sort order"
echo ""
echo "Edit the PR title, then re-run this job. The job reads the current title, so a re-run picks up the edit."

exit 1
