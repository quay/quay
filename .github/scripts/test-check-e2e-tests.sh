#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$script_dir/check-e2e-tests.sh"
workflow="$script_dir/../workflows/ci-web.yaml"

failures=0

# name | comma-separated changed files | expected exit | expected "Source code changes" count ("-" if not printed) | substring expected in output
cases=(
  'migration revision with its unit test|data/migrations/versions/4e2713248cf9_alter_label_and_manifestlabel_id.py,data/migrations/test/test_alter_label_and_manifestlabel_id.py|0|0|No significant source changes'
  'migration revision with tests, CI scripts, and Go test|.github/scripts/check-e2e-tests.sh,.github/scripts/test-check-e2e-tests.sh,.github/workflows/ci-web.yaml,data/migrations/test/test_alter_label_and_manifestlabel_id.py,data/migrations/versions/4e2713248cf9_alter_label_and_manifestlabel_id.py,internal/config/schema_test.go|0|0|No significant source changes'
  'migration revision only|data/migrations/versions/4e2713248cf9_alter_label_and_manifestlabel_id.py|0|0|No significant source changes'
  'migration test only|data/migrations/test/test_alter_label_and_manifestlabel_id.py|0|0|No significant source changes'
  'migration revision with a model change|data/migrations/versions/4e2713248cf9_alter_label_and_manifestlabel_id.py,data/database.py|1|1|includes no Playwright e2e tests'
  'migration revision, test, and API change|data/migrations/versions/4e2713248cf9_alter_label_and_manifestlabel_id.py,data/migrations/test/test_alter_label_and_manifestlabel_id.py,endpoints/api/label.py|1|1|includes no Playwright e2e tests'
  'migration environment is not a revision|data/migrations/env.py|1|1|includes no Playwright e2e tests'
  'nested path under versions is not a revision|data/migrations/versions/helpers/util.py|1|1|includes no Playwright e2e tests'
  'backend model change|data/model/oci/label.py|1|1|includes no Playwright e2e tests'
  'API change|endpoints/api/repository.py|1|1|includes no Playwright e2e tests'
  'UI change|web/src/routes/RepositoriesList/RepositoriesList.tsx|1|1|includes no Playwright e2e tests'
  'API change with Playwright spec|endpoints/api/repository.py,web/playwright/e2e/repository/repository-list.spec.ts|0|1|Playwright e2e tests were added or updated'
  'migration and model change with Playwright spec|data/migrations/versions/4e2713248cf9_alter_label_and_manifestlabel_id.py,data/database.py,web/playwright/e2e/repository/labels.spec.ts|0|1|Playwright e2e tests were added or updated'
  'dependency-only update|requirements.txt,web/package.json,web/pnpm-lock.yaml,go.sum|0|-|Dependency-only update detected'
  'config schema only|util/config/schema.py|0|0|No significant source changes'
  'backend and frontend unit tests only|data/model/test/test_label.py,web/src/libs/utils.test.ts|0|0|No significant source changes'
  'docs only|agent_docs/database.md|0|0|No significant source changes'
)

for case in "${cases[@]}"; do
  IFS='|' read -r name files expect_exit expect_source expect_substr <<<"$case"
  changed_files="$(tr ',' '\n' <<<"$files")"

  set +e
  output="$(CHANGED_FILES="$changed_files" bash "$script" 2>&1)"
  actual_exit=$?
  set -e

  if [ "$actual_exit" -ne "$expect_exit" ]; then
    echo "FAIL (expected exit $expect_exit, got $actual_exit): $name"
    echo "$output"
    failures=$((failures + 1))
    continue
  fi

  if [ "$expect_source" != "-" ] && ! grep -qxF "Source code changes: $expect_source" <<<"$output"; then
    echo "FAIL (expected 'Source code changes: $expect_source'): $name"
    echo "$output"
    failures=$((failures + 1))
    continue
  fi

  if ! grep -qF "$expect_substr" <<<"$output"; then
    echo "FAIL (missing expected output '$expect_substr'): $name"
    echo "$output"
    failures=$((failures + 1))
    continue
  fi

  echo "PASS: $name"
done

# The workflow must run this script rather than an inline copy of the logic.
if grep -qF '.github/scripts/check-e2e-tests.sh' "$workflow"; then
  echo "PASS: ci-web.yaml runs check-e2e-tests.sh"
else
  echo "FAIL: ci-web.yaml does not run check-e2e-tests.sh"
  failures=$((failures + 1))
fi

if [ "$failures" -ne 0 ]; then
  echo "$failures case(s) failed"
  exit 1
fi

echo "all cases passed"
exit 0
