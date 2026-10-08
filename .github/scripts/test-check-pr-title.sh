#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$script_dir/check-pr-title.sh"

# The PCRE regex this script replaces (ci-lint.yaml, pr-title-check job, before
# this change). Equivalence with the new script's ERE is asserted per case below.
old_pcre='^(?:\[redhat-[0-9]+\.[0-9]+\] )?(?:PROJQUAY-[0-9]+|QUAYIO-[0-9]+|NO-ISSUE): [a-z]+(?:\([^)]+\))?: .+$'

failures=0

# title | expect_pass (0/1) | substring expected in output when failing ("" if expect_pass)
cases=(
  'NO-ISSUE: Clarifications to the security policy|0|no conventional'
  'NO-ISSUE: docs: Clarifications to the security policy|1|'
  'PROJQUAY-10983: fix(mirroring): add isRequired to robot user field|1|'
  '[redhat-3.17] PROJQUAY-12461: fix(cve): bump postcss for CVE-2026-69153|1|'
  'QUAYIO-12345: feat(auth): add SSO support for quay.io|1|'
  'fix(api): no ticket|0|no ticket prefix'
  '[redhat-3.17]PROJQUAY-1: fix: x|0|no ticket prefix'
  'PROJQUAY-1: Fix: x|0|no conventional'
  'NO-ISSUE: é: x|0|no conventional'
)

for case in "${cases[@]}"; do
  IFS='|' read -r title expect_pass expect_substr <<<"$case"

  set +e
  output="$(PR_TITLE="$title" "$script" 2>&1)"
  actual_exit=$?
  set -e

  if [ "$expect_pass" = "1" ]; then
    if [ "$actual_exit" -ne 0 ]; then
      echo "FAIL (expected pass, got exit $actual_exit): $title"
      echo "$output"
      failures=$((failures + 1))
      continue
    fi
  else
    if [ "$actual_exit" -eq 0 ]; then
      echo "FAIL (expected failure, got pass): $title"
      failures=$((failures + 1))
      continue
    fi
    if ! grep -qF "$expect_substr" <<<"$output"; then
      echo "FAIL (missing expected part '$expect_substr'): $title"
      echo "$output"
      failures=$((failures + 1))
      continue
    fi
  fi

  # Equivalence with the old PCRE regex.
  if grep -qP "$old_pcre" <<<"$title"; then
    old_pass=1
  else
    old_pass=0
  fi
  if [ "$old_pass" != "$expect_pass" ]; then
    echo "FAIL (old regex disagrees, old_pass=$old_pass expect_pass=$expect_pass): $title"
    failures=$((failures + 1))
    continue
  fi

  echo "PASS: $title"
done

if [ "$failures" -ne 0 ]; then
  echo "$failures case(s) failed"
  exit 1
fi

echo "all cases passed"
exit 0
